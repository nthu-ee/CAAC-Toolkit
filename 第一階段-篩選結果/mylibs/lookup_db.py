import xlsxwriter


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
    def writeOutResult(outputFile, universityMap, departmentMap, lookupResult, args):
        # output the results (xlsx)
        with xlsxwriter.Workbook(outputFile) as xlsxfile:

            worksheet = xlsxfile.add_worksheet('篩選結果')
            worksheet.write_row(
                0, 0,
                [ '准考證號', '校名與系所' ]
            )

            rowCnt = 2
            for admissionId, departmentIds in lookupResult.items():
                applieds = [
                    # '國立臺灣大學 化學工程學系',
                    # ...
                ]
                for departmentId in departmentIds:
                    universityId = departmentId[:3]
                    applieds.append(
                        "{} {}".format(
                            universityMap[universityId],
                            departmentMap[departmentId],
                        )
                    )
                worksheet.write_row(
                    rowCnt, 0,
                    [ int(admissionId), *applieds ]
                )
                rowCnt += 1

    @staticmethod
    def writeOutResultNthuEe(outputFile, universityMap, departmentMap, lookupResult, args):

        def nthuSort(departmentId):
            universityId = departmentId[:3]

            if '清華大學' in universityMap[universityId]:
                if '電機工程' in departmentMap[departmentId]:
                    return '9' * 6 # 清大電機 should be the last one
                else:
                    return '9' * 3 + departmentId[-3:]
            else:
                return departmentId

        ArgsDepartmentIds = list(set( # list unique
            filter(len, args.departmentIds.split(','))
        ))

        # let's do some post processes
        # - we only want to show departments that are not in args.departmentIds
        # - we want 清大電機 to be shown as the last one
        postProcessedResults = {}
        for admissionId, departmentIds in lookupResult.items():
            # remove departments which are in args.departmentIds
            departmentIds = list(set(departmentIds) - set(ArgsDepartmentIds))
            # put 清大電機 to the last one
            departmentIds.sort(key=nthuSort)
            postProcessedResults[admissionId] = departmentIds

        lookup_db.writeOutResult(outputFile, universityMap, departmentMap, postProcessedResults, args)
