class lookup_db():

    @staticmethod
    def lookupByAdmissionIds(dbHandle, admissionIds):
        results = {
            # 准考證號: [ 錄取系所ID, ... ]
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
