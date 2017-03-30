import argparse
import csv
import datetime
import os
import sqlite3
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'mylibs'))
from lookup_db import lookup_db

YEAR_BEGIN = 1911

# change the working directory
try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

parser = argparse.ArgumentParser(description='A crawler for CAAC website.')
parser.add_argument(
    '--year',
    type=int,
    default=datetime.datetime.now().year - YEAR_BEGIN,
    help='The year of data to be crawled. (ex: 2017 or 106 is the same)',
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
    # 准考證號: [ 錄取系所ID, ... ]
    # ...
}

dbFilepath = os.path.join('crawler_{}'.format(year), 'sqlite3.db')
resultFilepath = os.path.join('result.csv')

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

    cursor = conn.execute('''
        SELECT admissionId
        FROM qualified
        WHERE departmentId IN ({})
    '''.format("'" + "','".join(departmentIds) + "'"))

    admissionIds = [ result[0] for result in cursor.fetchall() ]

    result = lookup_db.lookupByAdmissionIds(conn, admissionIds)
    results.update(result)

conn.close()

# delete the old CSV file
if os.path.isfile(resultFilepath):
    os.remove(resultFilepath)

# write result to a CSV file
with open(resultFilepath, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
    writer.writerow([
        '學測准考證號',
        '系所編號',
        '大學名稱',
        '大學系所',
    ])
    writer.writerow([]) # separator
    for admissionId, departmentIds in results.items():
        for departmentId in departmentIds:
            universityId = departmentId[:3]
            writer.writerow([
                admissionId,
                departmentId,
                universityMap[universityId],
                departmentMap[departmentId],
            ])
        writer.writerow([]) # separator

print(results)
