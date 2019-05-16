import argparse
import collections
import datetime
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from caac_package.LookupDb import LookupDb
from caac_package.ProjectConfig import ProjectConfig
from caac_package.Year import Year
import caac_package.functions as caac_funcs

parser = argparse.ArgumentParser(description="A database lookup utility for CAAC website.")
parser.add_argument(
    "--year",
    type=int,
    default=Year.YEAR_CURRENT,
    help="The year of data to be processed. (ex: 2017 or 106 is the same)",
)
parser.add_argument(
    "--admissionIds",
    default="",
    help="Admission IDs that are going to be looked up. (separate by commas)",
)
parser.add_argument(
    "--departmentIds",
    default="",
    help="Department IDs that are going to be looked up. (separate by commas)",
)
parser.add_argument(
    "--output",
    default=datetime.datetime.now().strftime("result_%Y%m%d_%H%M%S.xlsx"),
    help="The file to output results. (.xlsx file)",
)
parser.add_argument("--outputFormat", default="", help='Leave it blank or "NthuEe"')
args = parser.parse_args()

year = Year.taiwanize(args.year)
resultFilepath = (
    args.output if os.path.splitext(args.output)[1].lower() == ".xlsx" else f"{args.output}.xlsx"
)
dbFilepath = ProjectConfig.getCrawledDbFile(year, "apply_sieve")

# variables
results = {
    # '准考證號': [ '系所編號', ... ],
    # ...
}

lookup = LookupDb(dbFilepath)
lookup.loadDb()

# do lookup
if args.admissionIds:
    admissionIds = caac_funcs.listUnique(args.admissionIds.split(","), clear=True)
    result = lookup.lookupByAdmissionIds(admissionIds)
    results.update(result)

# do lookup
if args.departmentIds:
    departmentIds = caac_funcs.listUnique(args.departmentIds.split(","), clear=True)
    result = lookup.lookupByDepartmentIds(departmentIds)
    results.update(result)

# sort the result dict with admissionIds (ascending)
results = collections.OrderedDict(sorted(results.items()))

# delete the old xlsx file
if os.path.isfile(resultFilepath):
    os.remove(resultFilepath)

# write result to a xlsx file
writeOutMethod = f"writeOutResult{args.outputFormat}"
try:
    getattr(lookup, writeOutMethod)(resultFilepath, results, args)
except Exception:
    raise Exception(f"Unknown option: --outputFormat={args.outputFormat}")

print(results)
