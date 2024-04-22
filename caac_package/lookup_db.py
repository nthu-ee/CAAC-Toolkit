from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import xlsxwriter


class LookupDb:
    # db handle
    conn: sqlite3.Connection | None = None

    university_map: dict[str, str] = {}  # {"001: "國立臺灣大學", ...}
    department_map: dict[str, str] = {}  # {"001012": "中國文學系", ...}

    def __init__(self, db_file: str | Path) -> None:
        if not (db_file := Path(db_file)).is_file():
            raise Exception(f"DB file does not exist: {db_file}")

        self.conn = sqlite3.connect(db_file)

        cursor = self.conn.execute(
            """
                SELECT id, name
                FROM universities
            """
        )
        self.university_map = {university[0]: university[1] for university in cursor.fetchall()}

        cursor = self.conn.execute(
            """
                SELECT id, name
                FROM departments
            """
        )
        self.department_map = {department[0]: department[1] for department in cursor.fetchall()}

    def __del__(self) -> None:
        if self.conn:
            self.conn.close()

    def load_db(self) -> tuple[dict[str, str], dict[str, str]]:
        return self.university_map, self.department_map

    def lookup_by_admission_ids(self, admission_ids: Iterable[str]) -> dict[str, Any]:
        results: dict[str, list[str]] = {}  # {"准考證號": ["系所編號", ...], ...}

        assert self.conn
        for admission_id in admission_ids:
            cursor = self.conn.execute(
                """
                    SELECT department_id
                    FROM qualified
                    WHERE admission_id=?
                """,
                (admission_id,),
            )

            department_ids = [result[0] for result in cursor.fetchall()]
            results[admission_id] = department_ids

        return results

    def lookup_by_department_ids(self, department_ids: Iterable[str]) -> dict[str, Any]:
        assert self.conn
        cursor = self.conn.execute(
            """
                SELECT admission_id
                FROM qualified
                WHERE department_id IN ({})
            """.format("'" + "','".join(department_ids) + "'")
        )

        admission_ids = [result[0] for result in cursor.fetchall()]

        return self.lookup_by_admission_ids(admission_ids)

    def write_out_sieve_result(
        self,
        output_file: str,
        lookup_result: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        # output the results (xlsx)
        with xlsxwriter.Workbook(output_file) as wb:
            cell_format = wb.add_format({
                "align": "left",
                "valign": "vcenter",
                "text_wrap": True,
                "font_size": 9,
            })

            ws = wb.add_worksheet("第一階段-篩選結果（甄選委員會）")
            ws.freeze_panes(1, 1)

            ws.write_row(0, 0, ["准考證號", "校名與系所"], cell_format)

            for row_num, (admission_id, department_ids) in enumerate(lookup_result.items(), 1):
                applieds: list[str] = []  # ['國立臺灣大學 化學工程學系', ...]

                for department_id in department_ids:
                    university_id = department_id[:3]
                    applieds.append(f"{self.university_map[university_id]}\n{self.department_map[department_id]}")

                ws.write_row(row_num, 0, [int(admission_id), *applieds], cell_format)

    def write_out_sieve_result_nthu_ee(
        self,
        output_file: str,
        lookup_result: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        def nthu_sort(department_id: str) -> str:
            university_id = department_id[:3]

            if "清華大學" in self.university_map[university_id]:
                if "電機工程" in self.department_map[department_id]:
                    return "9" * 6  # 清大電機 should be the last one
                return "9" * 3 + department_id[-3:]
            return department_id

        # list unique
        args_department_ids = list(set(filter(None, args.department_ids.split(","))))

        # let's do some post processes
        # - we only want to show departments that are not in args.department_ids
        # - we want 清大電機 to be shown as the last one
        post_processed_results = {}
        for admission_id, department_ids in lookup_result.items():
            # remove departments which are in args.department_ids
            department_ids = list(set(department_ids) - set(args_department_ids))
            # put 清大電機 to the last one
            department_ids.sort(key=nthu_sort)
            post_processed_results[admission_id] = department_ids

        self.write_out_sieve_result(output_file, post_processed_results, args)

    def write_out_entrance_result(
        self,
        output_file: str,
        lookup_result: dict[str, Any],
        args: argparse.Namespace,
    ) -> None:
        # output the results (xlsx)
        with xlsxwriter.Workbook(output_file) as wb:
            cell_format = wb.add_format({
                "align": "left",
                "valign": "vcenter",
                "text_wrap": True,
                "font_size": 9,
            })

            ws = wb.add_worksheet("第二階段-分發結果（甄選委員會）")
            ws.freeze_panes(1, 1)

            ws.write_row(0, 0, ["准考證號", "分發結果"], cell_format)

            for row_num, (admission_id, department_ids) in enumerate(lookup_result.items(), 1):
                applieds: list[str] = []  # ['國立臺灣大學 化學工程學系', ...]

                for department_id in department_ids:
                    university_id = department_id[:3]
                    applieds.append(f"{self.university_map[university_id]}\n{self.department_map[department_id]}")

                ws.write_row(row_num, 0, [int(admission_id), *applieds], cell_format)
