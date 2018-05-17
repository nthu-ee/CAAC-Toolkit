import argparse
import datetime
import os
import sys
import time
import xlsxwriter

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from caac_package.ProjectConfig import ProjectConfig
from caac_package.Year import Year
import caac_package.functions as caac_funcs

parser = argparse.ArgumentParser(description='An utility for looking up Univerisy Entrance result.')
parser.add_argument(
    '--year',
    type=int,
    default=Year.YEAR_CURRENT,
    help='The year of data to be processed. (ex: 2017 or 106 is the same)',
)
parser.add_argument(
    '--batchSize',
    type=int,
    default=10,
    help='Fetch how many people from the internet at once?',
)
parser.add_argument(
    '--output',
    default=datetime.datetime.now().strftime('result_%Y%m%d_%H%M%S.xlsx'),
    help='The file to output results. (.xlsx file)',
)
args = parser.parse_args()

year = Year.taiwanize(args.year)
resultFilepath = args.output if os.path.splitext(args.output)[1].lower() == '.xlsx' else args.output + '.xlsx'
dbFilepath = ProjectConfig.getCrawledDbFilepath(year)

# variables
admissionIds = [] # 學測准考證

universityMap = {
    # '001': '國立臺灣大學',
    # ...
}
departmentMap = {
    # '001012': '中國文學系',
    # ...
}
lookupResults = {
    # '准考證號': {
    #     '_name': '考生姓名',
    #     '系所編號1': 'primary',
    #     ...
    # },
    # ...
}


def nthuSort(departmentId):
    global universityMap, departmentMap

    # special attribute like '_name'
    if departmentId[0] == '_':
        return departmentId

    universityId = departmentId[:3]
    universityName = universityMap[universityId]
    departmentName = departmentMap[departmentId]

    # 清華大學 be the later one
    if '清華大學' in universityName:
        # note that in ASCII code, 'Z' > 'B' > 'A'
        # 電機工程 be the later one
        if '電機工程' in departmentName:
            return 'Z' + departmentId
        # other department the the first
        else:
            return 'B' + departmentId
    # other university be the first
    else:
        return 'A' + departmentId


t_start = time.time()

universityMap, departmentMap = caac_funcs.loadDb(dbFilepath)

with open('admission_ids.txt', 'r') as f:
    admissionIds = f.read().split()
    # filter out those are not integers
    admissionIds = list(filter(lambda x: caac_funcs.canBeInt(x), admissionIds))
    # unique
    admissionIdsUnique = list(set(admissionIds))

# fetch data from the API
apiRetryInterval = 5
apiUrlFormat = 'https://freshman.tw/cross/{}/numbers/{}'
for admissionId_batch in caac_funcs.batch(admissionIdsUnique, args.batchSize):
    apiUrl = apiUrlFormat.format(year, ','.join(admissionId_batch))
    while True:
        content = caac_funcs.getPage(apiUrl)
        if content is None or '負載過大' in content:
            print('網站負載過大，{}秒後自動重試。'.format(apiRetryInterval))
            time.sleep(apiRetryInterval)
        else:
            break
    batchResults = caac_funcs.parseFreshmanTw(content)
    lookupResults.update(batchResults)
    print('[Fetched by admission IDs] {}'.format(', '.join(admissionId_batch)))

sheetFmts = {
    'base': {
        'align': 'left', 'valign': 'vcenter',
        'text_wrap': 1,
        'font_size': 9,
    },
    # 清大電機
    'nthuEe': {
        'bold': 1,
    },
    # 校系名稱
    'department': {
        'top': 1, 'bottom': 1, 'left': 1, 'right': 0,
    },
    # 榜單狀態
    'applyState': {
        'top': 1, 'bottom': 1, 'left': 0, 'right': 1,
    },
    # 榜單狀態：正取
    'applyState-primary': {
        'bg_color': '#99FF99',
    },
    # 榜單狀態：備取
    'applyState-spare': {
        'bg_color': '#FFFF99',
    },
    # 榜單狀態：落榜
    'applyState-failed': {
        'bg_color': '#FF9999',
    },
    # 榜單狀態：尚未公布
    'applyState-notYet': {
        'bg_color': '#D0D0D0',
    },
    # 榜單狀態：已分發
    'applyState-dispatched': {
        'bg_color': '#99D8FF',
    },
}

sheetData = [
    # (row 0)
    # [
    #     (column 0)
    #     { 'text': 'xxx', 'fmts': [ 'yyy', ... ] },
    #     ...
    # ],
    # (row 1)
    # [
    #     (column 0)
    #     { 'text': 'xxx', 'fmts': [ 'yyy', ... ] },
    #     ...
    # ],
    # ...
    [
        { 'text': '准考證號' },
        { 'text': '考生姓名' },
        { 'text': '校系名稱' },
        { 'text': '榜單狀態' },
    ],
]

# construct sheetData
for admissionId in admissionIds:
    if admissionId in lookupResults:
        row = []
        personResult = lookupResults[admissionId]

        row.append({ 'text': int(admissionId) })
        row.append({ 'text': personResult['_name'] })

        # we iterate the results in the order of department ID
        departmentIds = sorted(personResult.keys(), key=nthuSort)
        for departmentId in departmentIds:
            # special attribute like '_name'
            if departmentId[0] == '_':
                continue

            universityId = departmentId[:3]

            universityName = universityMap[universityId]
            departmentName = departmentMap[departmentId]
            departmentResult = personResult[departmentId]

            isDispatched = departmentResult['isDispatched']
            applyState = departmentResult['applyState'] # ex: 'spare-10'
            applyType = applyState.split('-')[0]        # ex: 'spare'

            if isDispatched:
                applyType = 'dispatched'

            row.append({
                'text': '{}\n{}'.format(universityName, departmentName),
                'fmts':
                    # NTHU specialization
                    [ 'department', 'nthuEe' ]
                    if '清華大學' in universityName and
                       '電機工程' in departmentName
                    else
                    [ 'department' ]
                ,
            })
            row.append({
                'text': '{} {}'.format(
                    '👑' if isDispatched else '',
                    caac_funcs.normalizeApplyStateE2C(applyState)
                ).strip(),
                'fmts': [
                    'applyState',
                    'applyState-{}'.format(applyType),
                ],
            })
        sheetData.append(row)
    else:
        print('[Warning] Cannot find the result for admission ID: {}'.format(admissionId))

# output the results (xlsx)
with xlsxwriter.Workbook(resultFilepath) as xlsxfile:

    worksheet = xlsxfile.add_worksheet('第二階段-交叉查榜')
    worksheet.freeze_panes(1, 2)

    rowCnt = 0
    for row in sheetData:
        colCnt = 0
        for col in row:
            # determine the cell format
            cellFmt = sheetFmts['base'].copy()
            if 'fmts' in col:
                for fmt in col['fmts']:
                    if fmt in sheetFmts:
                        cellFmt.update(sheetFmts[fmt])
            # apply the cell format
            worksheet.write(
                rowCnt, colCnt,
                col['text'],
                xlsxfile.add_format(cellFmt)
            )
            colCnt += 1
        rowCnt += 1

t_end = time.time()

print('[Done] It takes {} seconds.'.format(t_end - t_start))
