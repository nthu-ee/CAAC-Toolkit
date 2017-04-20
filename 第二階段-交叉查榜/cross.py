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

    if '清華大學' in universityMap[universityId]:
        if '電機工程' in departmentMap[departmentId]:
            return '9' * 6 # 清大電機 should be the last one
        else:
            return '9' * 3 + departmentId[-3:]
    else:
        return departmentId


t_start = time.time()

db = functions.loadDb(dbFilepath)
universityMap = db['universityMap']
departmentMap = db['departmentMap']

with open('admission_ids.txt', 'r') as f:
    admissionIds = f.read().split()
    # filter out those are not integers
    admissionIds = list(filter(lambda x: functions.canBeInt(x), admissionIds))
    # unique
    admissionIdsUnique = list(set(admissionIds))

apiUrlFormat = 'https://freshman.tw/cross/106/numbers/{}'
for admissionId_batch in functions.batch(admissionIdsUnique, args.batchSize):
    apiUrl = apiUrlFormat.format(','.join(admissionId_batch))
    retryInterval = 5
    while True:
        content = functions.getPage(apiUrl)
        if content is None or '負載過大' in content:
            print('網站負載過大，{}秒後自動重試。'.format(retryInterval))
            time.sleep(retryInterval)
        else:
            break
    batchResults = functions.parseFreshmanTw(content)
    lookupResults.update(batchResults)
    print('[Fetched by admission IDs] {}'.format(', '.join(admissionId_batch)))

sheet = [
    # (row 0)
    # [
    #     (column 0)
    #     { 'text': 'xxx', 'format': 'yyy' },
    #     ...
    # ],
    # (row 1)
    # [
    #     (column 0)
    #     { 'text': 'xxx', 'format': 'yyy' },
    #     ...
    # ],
    # ...
]

sheet.append([
    { 'text': '准考證號' },
    { 'text': '校系' },
    { 'text': '榜單狀態' },
])
for admissionId in admissionIds:
    if admissionId in lookupResults:
        row = []
        row.append({
            'text': int(admissionId),
        })
        personResult = lookupResults[admissionId]
        # we iterate the results in the order of department ID
        departmentIds = sorted(personResult.keys(), key=nthuSort)
        for departmentId in departmentIds:
            universityId = departmentId[:3]
            applyState = personResult[departmentId]
            row.append({
                'text': '{}\n{}'.format(
                    universityMap[universityId],
                    departmentMap[departmentId],
                ),
            })
            row.append({
                'text': functions.normalizeApplyStateE2C(applyState),
                'format': applyState.split('-')[0],
            })
        sheet.append(row)
    else:
        print('Cannot find the result for admission ID: {}'.format(admissionId))

# output the results (xlsx)
with xlsxwriter.Workbook(resultFilepath) as xlsxfile:
    formatBase = {
        'align': 'left',
        'valign': 'vcenter',
        'text_wrap': True,
        'font_size': 10,
    }
    formats = {
        '_base_': xlsxfile.add_format(formatBase),
        # 正取
        'primary': xlsxfile.add_format({ **formatBase, 'bg_color': '#66FF66' }),
        # 備取
        'spare': xlsxfile.add_format({ **formatBase, 'bg_color': '#FFFF66' }),
        # 落榜
        'failed': xlsxfile.add_format({ **formatBase, 'bg_color': '#FF6666' }),
        # 未公布
        'notYet': xlsxfile.add_format({ **formatBase, 'bg_color': '#C3C3C3' }),
    }

    worksheet = xlsxfile.add_worksheet('交叉查榜')
    worksheet.freeze_panes(1, 1)

    rowCnt = 0
    for row in sheet:
        colCnt = 0
        for col in row:
            if 'format' in col:
                worksheet.write(rowCnt, colCnt, col['text'], formats[col['format']])
            else:
                worksheet.write(rowCnt, colCnt, col['text'], formats['_base_'])
            colCnt += 1
        rowCnt += 1

t_end = time.time()

print('[Done] It takes {} seconds.'.format(t_end - t_start))
