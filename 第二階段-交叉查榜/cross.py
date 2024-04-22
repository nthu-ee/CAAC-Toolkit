from __future__ import annotations

import argparse
import asyncio
import datetime
import os
import re
import sys
import time
from typing import cast

import pandas as pd
from loguru import logger
from pyppeteer import launch
from xlsxwriter import Workbook

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import caac_package.functions as caac_funcs
from caac_package.year import Year

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
result_filepath = args.output if os.path.splitext(args.output)[1].lower() == ".xlsx" else args.output + ".xlsx"

# variables
cross_results = {
    # '准考證號': {
    #     '_name': '考生姓名',
    #     '系所編號1': {
    #         '_name': '國立臺灣大學醫學系(繁星第八類)',
    #         'is_dispatched': False,
    #         'apply_state': 'primary',
    #     }
    #     ...
    # },
    # ...
}


def fix_pyppeteer() -> None:
    """Help us be able to crawl Cloudflare-protected sites."""
    from pyppeteer import launcher

    # args are copied from https://www.npmjs.com/package/puppeteer-extra-plugin-stealth
    launcher.DEFAULT_ARGS = [
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-blink-features=AutomationControlled",
        "--disable-breakpad",
        "--disable-client-side-phishing-detection",
        "--disable-component-extensions-with-background-pages",
        "--disable-default-apps",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-features=RendererCodeIntegrity,Translate",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-popup-blocking",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--disable-sync",
        "--enable-automation",
        "--enable-blink-features=IdleDetection",
        "--enable-features=NetworkService,NetworkServiceInProcess",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--no-first-run",
        "--password-store=basic",
        "--use-mock-keychain",
    ]


def split_university_name_and_department_name(fullName: str) -> tuple[str, str]:
    """
    @brief 將 "國立臺灣大學機械工程學系" 轉換為 ['國立臺灣大學', '機械工程學系']

    @param fullName The full university + department name string

    @return (university_name, department_name)
    """
    if not (findUniverityName := re.search(r"((?:[^\s]+)(?:大學|學院))(.*)", fullName)):
        logger.error(f"Failed to split university name: {fullName}")
        return ("", "")

    return (findUniverityName.group(1).strip(), findUniverityName.group(2).strip())


def nthu_sort(department):
    department_id, _ = department

    # special attribute like '_name'
    if department_id.startswith("_"):
        return department_id

    university_name, department_name = split_university_name_and_department_name(person_result[department_id]["_name"])

    # 清華大學 be the later one
    if "清華大學" in university_name:
        # note that in ASCII code, 'Z' > 'B' > 'A'
        # 電機工程 be the later one
        if "電機工程" in department_name:
            return f"Z{department_id}"
        # other department the the first
        else:
            return f"B{department_id}"
    # other university be the first
    else:
        return f"A{department_id}"


fix_pyppeteer()

t_start = time.time()

with open("department_ids.txt") as f:
    department_ids = f.read().split()
    # trim spaces
    department_ids = map(str.strip, department_ids)
    # filter out those are not integers
    department_ids = filter(caac_funcs.can_be_int, department_ids)

# unique
department_ids_unique = list(caac_funcs.unique(department_ids))


async def puppet_fetch_cross_urls(urls) -> None:
    global cross_results

    browser = await launch(
        executablePath=str(caac_funcs.get_chromium_binary_path()),
        headless=False,
        userDataDir=str(caac_funcs.get_chromium_profile_dir()),
    )

    for url in urls:
        logger.info(f"Visit {url}")

        page = await browser.newPage()

        await page.goto(url)
        await page.waitForSelector("#footer")

        html = await page.content()
        cross_results.update(caac_funcs.parse_www_com_tw(html))

        await page.close()

    await browser.close()
    logger.info("Done crawling...")


asyncio.get_event_loop().run_until_complete(
    puppet_fetch_cross_urls(
        urls=[
            f"https://www.com.tw/cross/check_{department_id}_NO_0_{year}_0_3.html"
            for department_id in department_ids_unique
        ]
    )
)

sheet_fmts = {
    "base": {"align": "left", "valign": "vcenter", "text_wrap": 1, "font_size": 9},
    # 清大電機
    "nthuEe": {"bold": 1},
    # 校系名稱
    "department": {"top": 1, "bottom": 1, "left": 1, "right": 0},
    # 榜單狀態
    "apply_state": {"top": 1, "bottom": 1, "left": 0, "right": 1},
    # 榜單狀態：正取
    "apply_state-primary": {"bg_color": "#99FF99"},
    # 榜單狀態：備取
    "apply_state-spare": {"bg_color": "#FFFF99"},
    # 榜單狀態：落榜
    "apply_state-failed": {"bg_color": "#FF9999"},
    # 榜單狀態：未知（無資料）
    "apply_state-unknown": {"bg_color": "#D0D0D0"},
    # 榜單狀態：已分發
    "apply_state-dispatched": {"bg_color": "#99D8FF"},
}

sheet_data = [
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
        {"text": "准考證號"},
        {"text": "考生姓名"},
        {"text": "分發結果"},
        {"text": "校系名稱"},
        {"text": "榜單狀態"},
    ],
]

# get a sorted version cross_results by its key (admission_id)
cross_results_sorted = [(key, cross_results[key]) for key in sorted(cross_results.keys())]

# construct sheet_data
for admission_id, person_result in cross_results_sorted:
    # "准考證號": {
    #     "_name": "考生姓名",
    #     "系所編號1": {
    #         "_name": "國立臺灣大學醫學系(繁星第八類)",
    #         "is_dispatched": False,
    #         "apply_state": "primary",
    #     },
    #     ...
    # },
    # ...

    row = []
    row.append({"text": admission_id})
    row.append({"text": person_result["_name"]})

    # get the name of the dispatched department
    department_name_dispatched = [
        v["_name"] for k, v in person_result.items() if not k.startswith("_") and v["is_dispatched"]
    ]

    if department_name_dispatched:
        university_name, department_name = split_university_name_and_department_name(department_name_dispatched[0])
        department_name_dispatched = f"{university_name}\n{department_name}"
    else:
        department_name_dispatched = ""

    row.append({"text": department_name_dispatched})

    # we hope show NTHU's result as the last
    # so we construct a sorted department_ids to be used later
    person_result_sorted = sorted(person_result.items(), key=nthu_sort)
    department_ids_sorted = filter(caac_funcs.can_be_int, map(lambda department: department[0], person_result_sorted))

    # we iterate the results in the order of department ID
    for department_id in department_ids_sorted:
        # special attribute like '_name'
        if department_id.startswith("_"):
            continue

        university_name, department_name = split_university_name_and_department_name(
            person_result[department_id]["_name"]
        )

        department_result = person_result[department_id]

        is_dispatched = department_result["is_dispatched"]
        apply_state = department_result["apply_state"]  # ex: 'spare-10'
        apply_type = apply_state.split("-")[0]  # ex: 'spare'

        if is_dispatched:
            apply_type = "dispatched"

        row.append({
            "text": f"{university_name}\n{department_name}",
            "fmts": (
                # NTHU specialization
                ["department", "nthuEe"]
                if "清華大學" in university_name and "電機工程" in department_name
                else ["department"]
            ),
        })

        apply_state_icon = "👑" if is_dispatched else ""
        apply_state_normalized = caac_funcs.normalize_apply_state_e2c(apply_state)

        row.append({
            "text": f"{apply_state_icon} {apply_state_normalized}".strip(),
            "fmts": ["apply_state", f"apply_state-{apply_type}"],
        })
    sheet_data.append(row)

# output the results (xlsx)
with pd.ExcelWriter(result_filepath, engine="xlsxwriter") as writer:
    workbook = cast(Workbook, writer.book)

    worksheet = workbook.add_worksheet("第二階段-交叉查榜")
    worksheet.freeze_panes(1, 3)

    row_cnt = 0
    for row in sheet_data:
        col_cnt = 0
        for col in row:
            # determine the cell format
            cell_fmt = sheet_fmts["base"].copy()
            if "fmts" in col:
                for fmt in col["fmts"]:
                    if fmt in sheet_fmts:
                        cell_fmt.update(sheet_fmts[fmt])
            # apply the cell format
            worksheet.write(row_cnt, col_cnt, col["text"], workbook.add_format(cell_fmt))
            col_cnt += 1
        row_cnt += 1

t_end = time.time()

logger.info(f"[Done] It takes {t_end - t_start} seconds.")
