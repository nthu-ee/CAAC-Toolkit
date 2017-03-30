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
