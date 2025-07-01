from __future__ import annotations

import argparse
import datetime
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import caac_package.functions as caac_funcs
from caac_package.lookup_db import LookupDb
from caac_package.project_config import ProjectConfig

parser = argparse.ArgumentParser(description="A database lookup utility for CAAC website.")
parser.add_argument(
    "--year",
    type=int,
    default=None,
    help="The year of data to be processed. (ex: 2017 or 106 is the same)",
)
parser.add_argument(
    "--admission-ids",
    default="",
    help="Admission IDs that are going to be looked up. (separate by commas)",
)
parser.add_argument(
    "--department-ids",
    default="",
    help="Department IDs that are going to be looked up. (separate by commas)",
)
parser.add_argument(
    "--output",
    default=datetime.datetime.now().strftime("result_%Y%m%d_%H%M%S.xlsx"),
    help="The file to output results. (.xlsx file)",
)
parser.add_argument("--output-format", default="", help='Leave it blank or "NthuEe"')
args = parser.parse_args()

# 自動從路徑中提取年份
current_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(current_dir, ".."))  # 回到專案根目錄
data_dir = os.path.join(project_root, "data")

# 找出 crawler_XXXX 的資料夾
for folder in os.listdir(data_dir):
    if folder.startswith("crawler_"):
        year_str = folder.split("_")[-1]
        if year_str.isdigit():
            year = int(year_str)
            break
else:
    raise FileNotFoundError("找不到以 crawler_ 開頭的資料夾！請確認 data/ 路徑下有 crawler_XXXX 的資料夾。")

result_filepath = args.output if os.path.splitext(args.output)[1].lower() == ".xlsx" else f"{args.output}.xlsx"
db_filepath = ProjectConfig.get_crawled_db_file(year, "apply_entrance")

# variables
results = {
    # '准考證號': [ '系所編號', ... ],
    # ...
}

lookup = LookupDb(db_filepath)
lookup.load_db()

# do lookup
if args.admission_ids:
    if args.admission_ids == "@file":
        with open("admission_ids.txt") as f:
            admission_ids = f.read().split()
            # trim spaces
            admission_ids = map(str.strip, admission_ids)
            # filter out those are not integers
            admission_ids = filter(caac_funcs.can_be_int, admission_ids)
    else:
        admission_ids = args.admission_ids.split(",")

    admission_ids = list(caac_funcs.unique(admission_ids, clear=True))

    result = lookup.lookup_by_admission_ids(admission_ids)
    results.update(result)

# do lookup
if args.department_ids:
    if args.department_ids == "@file":
        with open("department_ids.txt") as f:
            department_ids = f.read().split()
            # trim spaces
            department_ids = map(str.strip, department_ids)
            # filter out those are not integers
            department_ids = filter(caac_funcs.can_be_int, department_ids)
    else:
        department_ids = args.department_ids.split(",")

    department_ids = list(caac_funcs.unique(department_ids, clear=True))

    result = lookup.lookup_by_department_ids(department_ids)
    results.update(result)

# sort the result dict with admission_ids (ascending)
results = dict(sorted(results.items()))

# delete the old xlsx file
if os.path.isfile(result_filepath):
    os.remove(result_filepath)

# write result to a xlsx file
output_format = args.output_format
output_format_prefixed = f"_{output_format}" if output_format else ""
write_out_method = f"write_out_entrance_result{output_format_prefixed}"
try:
    getattr(lookup, write_out_method)(result_filepath, results, args)
except Exception:
    raise Exception(f"Unknown option: --output-format={output_format}")

print(results)
