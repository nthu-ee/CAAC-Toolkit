import argparse
import datetime
import os
import sys
import time
import xlsxwriter

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'mylibs'))
from project_config import project_config
import functions

YEAR_BEGIN = 1911
YEAR_CURRENT = datetime.datetime.now().year - YEAR_BEGIN

# change the working directory
try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

parser = argparse.ArgumentParser(description='An utility for looking up Univerisy Entrance result.')
parser.add_argument(
    '--year',
    type=int,
    default=YEAR_CURRENT,
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

year = args.year - YEAR_BEGIN if args.year >= YEAR_BEGIN else args.year
dbFilepath = os.path.join(project_config.resultDir.format(year), 'sqlite3.db')
resultFilepath = args.output if os.path.splitext(args.output)[1].lower() == '.xlsx' else args.output + '.xlsx'

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
    #     '系所編號': 'primary',
    #     ...
    # },
    # ...
}


def nthuSort(departmentId):
    global universityMap, departmentMap

    universityId = departmentId[:3]
    universityName = universityMap[universityId]
    departmentName = departmentMap[departmentId]

    # 清華大學 be the later one
    if '清華大學' in universityName:
        # 電機工程 be the later one
        if '電機工程' in departmentName:
            # 甲組 be the first
            if '甲組' in departmentName:
                return '9' * 3 + '990'
            # 乙組 be the later
            else:
                return '9' * 3 + '999'
        # other department the the first
        else:
            return '9' * 3 + departmentId[-3:]
    # other university be the first
    else:
        return departmentId


t_start = time.time()

universityMap, departmentMap = functions.loadDb(dbFilepath)

with open('admission_ids.txt', 'r') as f:
    admissionIds = f.read().split()
    # filter out those are not integers
    admissionIds = list(filter(lambda x: functions.canBeInt(x), admissionIds))
    # unique
    admissionIdsUnique = list(set(admissionIds))

apiRetryInterval = 5
apiUrlFormat = 'https://freshman.tw/cross/{}/numbers/{}'
for admissionId_batch in functions.batch(admissionIdsUnique, args.batchSize):
    apiUrl = apiUrlFormat.format(year, ','.join(admissionId_batch))
    while True:
        content = functions.getPage(apiUrl)
        if content is None or '負載過大' in content:
            print('網站負載過大，{}秒後自動重試。'.format(apiRetryInterval))
            time.sleep(apiRetryInterval)
        else:
            break
    batchResults = functions.parseFreshmanTw(content)
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
    # 准考證號
    'admissionId': {},
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
        { 'text': '校系名稱' },
        { 'text': '榜單狀態' },
    ],
]

for admissionId in admissionIds:
    if admissionId in lookupResults:
        row = []
        row.append({
            'text': int(admissionId),
            'fmts': [ 'admissionId' ],
        })
        personResult = lookupResults[admissionId]
        # we iterate the results in the order of department ID
        departmentIds = sorted(personResult.keys(), key=nthuSort)
        for departmentId in departmentIds:
            universityId = departmentId[:3]

            universityName = universityMap[universityId]
            departmentName = departmentMap[departmentId]
            applyState = personResult[departmentId] # ex: spare-10, notYet
            applyType = applyState.split('-')[0]    # ex: spare,    notYet

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
                'text': functions.normalizeApplyStateE2C(applyState),
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
    worksheet.freeze_panes(1, 1)

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
