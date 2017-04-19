import argparse
import collections
import datetime
import os
import sqlite3
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'mylibs'))
from project_config import project_config
from lookup_db import lookup_db

YEAR_BEGIN = 1911
YEAR_CURRENT = datetime.datetime.now().year - YEAR_BEGIN

# change the working directory
try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

parser = argparse.ArgumentParser(description='A crawler for CAAC website.')
parser.add_argument(
    '--year',
    type=int,
    default=YEAR_CURRENT,
    help='The year of data to be processed. (ex: 2017 or 106 is the same)',
)
parser.add_argument(
    '--admissionIds',
    default='',
    help='Admission IDs that are going to be looked up. (separate by commas)',
)
parser.add_argument(
    '--departmentIds',
    default='',
    help='Department IDs that are going to be looked up. (separate by commas)',
)
parser.add_argument(
    '--output',
    default='result.csv',
    help='The file to output results. (.csv file)',
)
parser.add_argument(
    '--outputFormat',
    default='',
    help='Leave it blank or "NthuEe"',
)
args = parser.parse_args()

year = args.year - YEAR_BEGIN if args.year >= YEAR_BEGIN else args.year

universityMap = {
    # '001': '國立臺灣大學',
    # ...
}
departmentMap = {
    # '001012': '中國文學系',
    # ...
}
results = {
    # '准考證號': [ '系所編號', ... ],
    # ...
}

dbFilepath = os.path.join(project_config.resultDir.format(year), 'sqlite3.db')
resultFilepath = args.output if os.path.splitext(args.output)[1].lower() == '.csv' else args.output + '.csv'

if not os.path.isfile(dbFilepath):
    raise Exception('DB file does not exist: {}'.format(dbFilepath))

conn = sqlite3.connect(dbFilepath)

# build universityMap
cursor = conn.execute('''
    SELECT id, name
    FROM universities
''')
for university in cursor.fetchall():
    universityMap[university[0]] = university[1]

# build departmentMap
cursor = conn.execute('''
    SELECT id, name
    FROM departments
''')
for department in cursor.fetchall():
    departmentMap[department[0]] = department[1]

# do lookup
if args.admissionIds:
    admissionIds = list(set( # list unique
        filter(len, args.admissionIds.split(','))
    ))

    result = lookup_db.lookupByAdmissionIds(conn, admissionIds)
    results.update(result)

# do lookup
if args.departmentIds:
    departmentIds = list(set( # list unique
        filter(len, args.departmentIds.split(','))
    ))

    result = lookup_db.lookupByDepartmentIds(conn, departmentIds)
    results.update(result)

conn.close()

# sort the result dict with admissionIds (ascending)
results = collections.OrderedDict(sorted(results.items()))

# delete the old CSV file
if os.path.isfile(resultFilepath):
    os.remove(resultFilepath)

# write result to a CSV file
writeOutMethod = 'writeOutResult{}'.format(args.outputFormat)
try:
    getattr(lookup_db, writeOutMethod)(
        resultFilepath,
        universityMap,
        departmentMap,
        results,
        args,
    )
except:
    raise Exception('Unknown option: --outputFormat={}'.format(args.outputFormat))

print(results)
