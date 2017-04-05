import csv


class lookup_db():

    @staticmethod
    def lookupByAdmissionIds(dbHandle, admissionIds):
        results = {
            # '准考證號': [ '系所編號', ... ],
            # ...
        }

        for admissionId in admissionIds:

            cursor = dbHandle.execute('''
                SELECT departmentId
                FROM qualified
                WHERE admissionId=?
            ''', (admissionId,))

            departmentIds = [ result[0] for result in cursor.fetchall() ]
            results[admissionId] = departmentIds

        return results

    @staticmethod
    def lookupByDepartmentIds(dbHandle, departmentIds):
        cursor = dbHandle.execute('''
            SELECT admissionId
            FROM qualified
            WHERE departmentId IN ({})
        '''.format("'" + "','".join(departmentIds) + "'"))

        admissionIds = [ result[0] for result in cursor.fetchall() ]

        return lookup_db.lookupByAdmissionIds(dbHandle, admissionIds)

    @staticmethod
    def writeOutResult(outputFile, universityMap, departmentMap, lookupResult):
        with open(outputFile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
            writer.writerow([
                '准考證號',
                '系所編號',
                '校名',
                '系所',
            ])
            writer.writerow([]) # separator
            for admissionId, departmentIds in lookupResult.items():
                for departmentId in departmentIds:
                    universityId = departmentId[:3]
                    writer.writerow([
                        admissionId,
                        departmentId,
                        universityMap[universityId],
                        departmentMap[departmentId],
                    ])
                writer.writerow([]) # separator
