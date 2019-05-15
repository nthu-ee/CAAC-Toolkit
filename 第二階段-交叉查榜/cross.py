import argparse
import datetime
import os
import pandas as pd
import re
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from caac_package.ProjectConfig import ProjectConfig
from caac_package.Year import Year
import caac_package.functions as caac_funcs

parser = argparse.ArgumentParser(description="An utility for looking up Univerisy Entrance result.")
parser.add_argument(
    "--year",
    type=int,
    default=Year.YEAR_CURRENT,
    help="The year of data to be processed. (ex: 2017 or 106 is the same)",
)
parser.add_argument(
    "--output",
    default=datetime.datetime.now().strftime("result_%Y%m%d_%H%M%S.xlsx"),
    help="The file to output results. (.xlsx file)",
)
args = parser.parse_args()

year = Year.taiwanize(args.year)
resultFilepath = (
    args.output if os.path.splitext(args.output)[1].lower() == ".xlsx" else args.output + ".xlsx"
)

# variables
crossResults = {
    # '准考證號': {
    #     '_name': '考生姓名',
    #         '系所編號1': {
    #             '_name': '國立臺灣大學醫學系(繁星第八類)',
    #             'isDispatched': False,
    #             'applyState': 'primary',
    #         }
    #     ...
    # },
    # ...
}


def splitUniversityNameAndDepartmentName(fullName):
    findUniverityName = re.search(r"((?:[^\s]+)(?:大學|學院))(.*)", fullName)

    if findUniverityName is None:
        return None

    return [findUniverityName.group(1).strip(), findUniverityName.group(2).strip()]


def nthuSort(department):
    departmentId, departmentResult = department

    # special attribute like '_name'
    if departmentId.startswith("_"):
        return departmentId

    universityName, departmentName = splitUniversityNameAndDepartmentName(
        personResult[departmentId]["_name"]
    )

    # 清華大學 be the later one
    if "清華大學" in universityName:
        # note that in ASCII code, 'Z' > 'B' > 'A'
        # 電機工程 be the later one
        if "電機工程" in departmentName:
            return "Z" + departmentId
        # other department the the first
        else:
            return "B" + departmentId
    # other university be the first
    else:
        return "A" + departmentId


t_start = time.time()

with open("department_ids.txt", "r") as f:
    departmentIds = f.read().split()
    # trim spaces
    departmentIds = [departmentId.strip() for departmentId in departmentIds]
    # filter out those are not integers
    departmentIds = list(filter(lambda x: caac_funcs.canBeInt(x), departmentIds))
    # unique
    departmentIdsUnique = list(set(departmentIds))

# fetch html content
apiRetryInterval = 5
apiUrlFormat = "https://www.com.tw/cross/check_{departmentId}_NO_0_{year}_0_3.html"
for departmentId in departmentIdsUnique:
    apiUrl = apiUrlFormat.format(departmentId=departmentId, year=year)

    while True:
        content = caac_funcs.getPage(apiUrl)
        print(f"[Fetching departmentId ID] {departmentId}")

        if content is None:
            print(f"網站負載過大，{apiRetryInterval}秒後自動重試。")
            time.sleep(apiRetryInterval)
        else:
            crossResults.update(caac_funcs.parseWwwComTw(content))
            break

sheetFmts = {
    "base": {"align": "left", "valign": "vcenter", "text_wrap": 1, "font_size": 9},
    # 清大電機
    "nthuEe": {"bold": 1},
    # 校系名稱
    "department": {"top": 1, "bottom": 1, "left": 1, "right": 0},
    # 榜單狀態
    "applyState": {"top": 1, "bottom": 1, "left": 0, "right": 1},
    # 榜單狀態：正取
    "applyState-primary": {"bg_color": "#99FF99"},
    # 榜單狀態：備取
    "applyState-spare": {"bg_color": "#FFFF99"},
    # 榜單狀態：落榜
    "applyState-failed": {"bg_color": "#FF9999"},
    # 榜單狀態：未知（無資料）
    "applyState-unknown": {"bg_color": "#D0D0D0"},
    # 榜單狀態：已分發
    "applyState-dispatched": {"bg_color": "#99D8FF"},
}

# fmt: off
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
        { 'text': '分發結果' },
        { 'text': '校系名稱' },
        { 'text': '榜單狀態' },
    ],
]
# fmt: on

# get a sorted version crossResults by its key (admissionId)
crossResultsSorted = [(key, crossResults[key]) for key in sorted(crossResults.keys())]

# construct sheetData
for crossResult in crossResultsSorted:
    admissionId, personResult = crossResult

    # '准考證號': {
    #     '_name': '考生姓名',
    #     '系所編號1': {
    #         '_name': '國立臺灣大學醫學系(繁星第八類)',
    #         'isDispatched': False,
    #         'applyState': 'primary',
    #     },
    #     ...
    # },
    # ...

    row = []
    row.append({"text": admissionId})
    row.append({"text": personResult["_name"]})

    # get the name of the dispatched department
    departmentNameDispatched = [
        v["_name"] for k, v in personResult.items() if not k.startswith("_") and v["isDispatched"]
    ]

    if departmentNameDispatched:
        universityName, departmentName = splitUniversityNameAndDepartmentName(
            departmentNameDispatched[0]
        )
        departmentNameDispatched = f"{universityName}\n{departmentName}"
    else:
        departmentNameDispatched = ""

    row.append({"text": departmentNameDispatched})

    # we hope show NTHU's result as the last
    # so we construct a sorted departmentIds to be used later
    personResultSorted = sorted(personResult.items(), key=nthuSort)
    departmentIdsSorted = map(
        lambda department: department[0],
        filter(lambda department: caac_funcs.canBeInt(department[0]), personResultSorted),
    )

    # we iterate the results in the order of department ID
    for departmentId in departmentIdsSorted:
        # special attribute like '_name'
        if departmentId.startswith("_"):
            continue

        universityName, departmentName = splitUniversityNameAndDepartmentName(
            personResult[departmentId]["_name"]
        )

        departmentResult = personResult[departmentId]

        isDispatched = departmentResult["isDispatched"]
        applyState = departmentResult["applyState"]  # ex: 'spare-10'
        applyType = applyState.split("-")[0]  # ex: 'spare'

        if isDispatched:
            applyType = "dispatched"

        row.append(
            {
                "text": f"{universityName}\n{departmentName}",
                "fmts": (
                    # NTHU specialization
                    ["department", "nthuEe"]
                    if "清華大學" in universityName and "電機工程" in departmentName
                    else ["department"]
                ),
            }
        )

        applyStateIcon = "👑" if isDispatched else ""
        applyStateNormalized = caac_funcs.normalizeApplyStateE2C(applyState)

        row.append(
            {
                "text": f"{applyStateIcon} {applyStateNormalized}".strip(),
                "fmts": ["applyState", f"applyState-{applyType}"],
            }
        )
    sheetData.append(row)

# output the results (xlsx)
with pd.ExcelWriter(resultFilepath, engine="xlsxwriter") as writer:
    workbook = writer.book

    worksheet = workbook.add_worksheet("第二階段-交叉查榜")
    worksheet.freeze_panes(1, 2)

    rowCnt = 0
    for row in sheetData:
        colCnt = 0
        for col in row:
            # determine the cell format
            cellFmt = sheetFmts["base"].copy()
            if "fmts" in col:
                for fmt in col["fmts"]:
                    if fmt in sheetFmts:
                        cellFmt.update(sheetFmts[fmt])
            # apply the cell format
            worksheet.write(rowCnt, colCnt, col["text"], workbook.add_format(cellFmt))
            colCnt += 1
        rowCnt += 1

t_end = time.time()

print(f"[Done] It takes {t_end - t_start} seconds.")
