from __future__ import annotations

import argparse
import os
import sqlite3
from collections.abc import Iterable
from typing import Any

import pandas as pd


class LookupDb:
    # db handle
    conn: sqlite3.Connection | None = None

    # universityMap = {
    #     '001': '國立臺灣大學',
    #     ...
    # }
    universityMap = {}

    # departmentMap = {
    #     '001012': '中國文學系',
    #     ...
    # }
    departmentMap = {}

    def __init__(self, dbFilepath: str) -> None:
        if not os.path.isfile(dbFilepath):
            raise Exception(f"DB file does not exist: {dbFilepath}")

        self.conn = sqlite3.connect(dbFilepath)

        cursor = self.conn.execute(
            """
                SELECT id, name
                FROM universities
            """
        )
        self.universityMap = {university[0]: university[1] for university in cursor.fetchall()}

        cursor = self.conn.execute(
            """
                SELECT id, name
                FROM departments
            """
        )
        self.departmentMap = {department[0]: department[1] for department in cursor.fetchall()}

    def __del__(self):
        if self.conn is not None:
            self.conn.close()

    def loadDb(self):
        return self.universityMap, self.departmentMap

    def lookupByAdmissionIds(self, admissionIds: Iterable[str]) -> dict[str, Any]:
        results = {
            # '准考證號': [ '系所編號', ... ],
            # ...
        }

        assert self.conn
        for admissionId in admissionIds:
            cursor = self.conn.execute(
                """
                    SELECT departmentId
                    FROM qualified
                    WHERE admissionId=?
                """,
                (admissionId,),
            )

            departmentIds = [result[0] for result in cursor.fetchall()]
            results[admissionId] = departmentIds

        return results

    def lookupByDepartmentIds(self, departmentIds: Iterable[str]) -> dict[str, Any]:
        assert self.conn
        cursor = self.conn.execute(
            """
                SELECT admissionId
                FROM qualified
                WHERE departmentId IN ({})
            """.format("'" + "','".join(departmentIds) + "'")
        )

        admissionIds = [result[0] for result in cursor.fetchall()]

        return self.lookupByAdmissionIds(admissionIds)

    def writeOutSieveResult(
        self,
        outputFile: str,
        lookupResult: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        # output the results (xlsx)
        with pd.ExcelWriter(outputFile, engine="xlsxwriter") as writer:
            workbook = writer.book

            cellFormat = workbook.add_format({
                "align": "left",
                "valign": "vcenter",
                "text_wrap": True,
                "font_size": 9,
            })

            worksheet = workbook.add_worksheet("第一階段-篩選結果（甄選委員會）")
            worksheet.freeze_panes(1, 1)

            worksheet.write_row(0, 0, ["准考證號", "校名與系所"], cellFormat)

            rowCnt = 1
            for admissionId, departmentIds in lookupResult.items():
                applieds = [
                    # '國立臺灣大學 化學工程學系',
                    # ...
                ]

                for departmentId in departmentIds:
                    universityId = departmentId[:3]
                    applieds.append(f"{self.universityMap[universityId]}\n{self.departmentMap[departmentId]}")

                worksheet.write_row(rowCnt, 0, [int(admissionId), *applieds], cellFormat)

                rowCnt += 1

    def writeOutSieveResultNthuEe(
        self,
        outputFile: str,
        lookupResult: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        def nthuSort(departmentId):
            universityId = departmentId[:3]

            if "清華大學" in self.universityMap[universityId]:
                if "電機工程" in self.departmentMap[departmentId]:
                    return "9" * 6  # 清大電機 should be the last one
                else:
                    return "9" * 3 + departmentId[-3:]
            else:
                return departmentId

        # list unique
        ArgsDepartmentIds = list(set(filter(None, args.departmentIds.split(","))))

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

        self.writeOutSieveResult(outputFile, postProcessedResults, args)

    def writeOutEntranceResult(
        self,
        outputFile: str,
        lookupResult: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        # output the results (xlsx)
        with pd.ExcelWriter(outputFile, engine="xlsxwriter") as writer:
            workbook = writer.book

            cellFormat = workbook.add_format({
                "align": "left",
                "valign": "vcenter",
                "text_wrap": True,
                "font_size": 9,
            })

            worksheet = workbook.add_worksheet("第二階段-分發結果（甄選委員會）")
            worksheet.freeze_panes(1, 1)

            worksheet.write_row(0, 0, ["准考證號", "分發結果"], cellFormat)

            rowCnt = 1
            for admissionId, departmentIds in lookupResult.items():
                applieds = [
                    # '國立臺灣大學 化學工程學系',
                    # ...
                ]

                for departmentId in departmentIds:
                    universityId = departmentId[:3]
                    applieds.append(f"{self.universityMap[universityId]}\n{self.departmentMap[departmentId]}")

                worksheet.write_row(rowCnt, 0, [int(admissionId), *applieds], cellFormat)

                rowCnt += 1
