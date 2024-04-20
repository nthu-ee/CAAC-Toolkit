from __future__ import annotations

import codecs
import os
import re
import sqlite3
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor

import cloudscraper
import lxml
import lxml.etree
from pyquery import PyQuery as pq

from .ProjectConfig import ProjectConfig


class Crawler:
    year = 0
    projectBaseUrl = ""

    collegeListUrl = ""
    resultDir = ""

    def __init__(self, year: int, apply_stage: str, projectBaseUrl: str = "") -> None:
        self.year = year
        self.apply_stage = apply_stage
        self.resultDir = ProjectConfig.getCrawledResultDir(self.year, self.apply_stage)

        # -------------- #
        # projectBaseUrl #
        # -------------- #
        self.projectBaseUrl = projectBaseUrl.strip()
        """
        Eventually, we have something like the following
        `https://www.cac.edu.tw/CacLink/apply113/113applY_xSievePk4g_T43D54VO_91S/html_sieve_113_Ks7Zx/ColPost/`
        """

        if re.search(r"\.[a-zA-Z0-9_]+$", self.projectBaseUrl):
            self.projectBaseUrl = os.path.dirname(self.projectBaseUrl)

        # ensure trailing backslash
        self.projectBaseUrl = self.projectBaseUrl.rstrip("/") + "/"

        self.projectBaseUrl = self.projectBaseUrl.format(self.year)

        # -------------- #
        # collegeListUrl #
        # -------------- #
        self.collegeListUrl = self.projectBaseUrl + "collegeList.htm"

    def run(self, showMessage: bool = False) -> None:
        # prepare the result directory
        os.makedirs(self.resultDir, exist_ok=True)

        filepaths = self.fetchAndSaveCollegeList()
        filepaths = self.fetchAndSaveDepartmentLists(filepaths)
        self.fetchAndSaveDepartmentApplys(filepaths)
        self.generateDb()

        if showMessage:
            print(f"[Crawler] Files are stored in: {self.resultDir}")

    def fetchAndSaveCollegeList(self) -> list[str]:
        departmentLists: list[str] = []

        # the user may give a wrong URL in the last run
        # in that case, we overwrite the old file and run again
        try:
            content = self.fetchAndSavePage(self.collegeListUrl, overwrite=False, log=True)
            links = pq(content)("a")
        except lxml.etree.ParserError:
            content = self.fetchAndSavePage(self.collegeListUrl, overwrite=True, log=True)
            links = pq(content)("a")

        for link in links.items():
            href = str(link.attr("href"))
            if href.startswith("web/"):
                departmentLists.append(href)

        return departmentLists

    def fetchAndSaveDepartmentLists(self, filepaths: Iterable[str]) -> list[str]:
        departmentApplys: list[str] = []

        def workerFetchPage(filepath: str) -> None:
            content = self.fetchAndSavePage(f"{self.projectBaseUrl}{filepath}", overwrite=False, log=True)
            links = pq(content)("a")
            for link in links.items():
                href = str(link.attr("href"))
                print(f"{filepath = }; {href = }")
                if href.startswith(("common/", "extra/")):
                    departmentApplys.append(self.simplifyUrl(f"web/{href}"))

        with ThreadPoolExecutor(max_workers=ProjectConfig.CRAWLER_WORKER_NUM) as executor:
            for filepath in filepaths:
                executor.submit(workerFetchPage, filepath=filepath)

        return departmentApplys

    def fetchAndSaveDepartmentApplys(self, filepaths: Iterable[str]) -> None:
        def workerFetchPage(filepath: str) -> None:
            self.fetchAndSavePage(f"{self.projectBaseUrl}{filepath}", overwrite=False, log=True)

        with ThreadPoolExecutor(max_workers=ProjectConfig.CRAWLER_WORKER_NUM) as executor:
            for filepath in filepaths:
                executor.submit(workerFetchPage, filepath=filepath)

        print("[crawler_caac] Finish crawling.")

    def fetchAndSavePage(self, url: str, overwrite: bool = True, log: bool = False) -> str:
        """fetch and save a page depending on its URL"""

        filepath = url.replace(self.projectBaseUrl, "")
        filepathAbsolute = os.path.join(self.resultDir, filepath)
        if not overwrite and os.path.isfile(filepathAbsolute):
            with open(filepathAbsolute, encoding="utf-8") as f:
                if log is True:
                    print(f"[Local] {url}")
                return f.read()

        if log is True:
            print(f"[Fetch] {url}")

        content = self.getPage(url) or ""
        self.writeFile(filepathAbsolute, content)
        return content

    def generateDb(self) -> None:
        """generate a db file from crawled html files"""

        dbFilepath = ProjectConfig.getCrawledDbFile(self.year, self.apply_stage)

        universityMap = {
            # '001': '國立臺灣大學',
            # ...
        }
        departmentMap = {
            # '001012': '中國文學系',
            # ...
        }
        departmentToAdmittees = {
            # '001012': [ '10006201', ... ],
            # ...
        }

        print("[crawler_caac] DB Gen: gathering data from the source...")

        # build universityMap
        with open(os.path.join(self.resultDir, "collegeList.htm"), encoding="utf-8") as f:
            content = f.read()
            founds = re.finditer(r"\(([0-9]{3})\)\d*([\w\s]+)", content)
            for found in founds:
                # let's find something like "(013)國立交通大學"
                universityMap[found.group(1)] = found.group(2).strip()

        # build departmentMap and departmentToAdmittees
        for subdir, dirs, files in os.walk(self.resultDir):
            print(f"Extract data from {subdir}")

            for file in files:
                # if not re.match(r'^[0-9]{6}\.(?:html?)$', file):
                #     continue

                if os.path.splitext(file)[1] not in [".htm", ".html"]:
                    continue

                departmentId = os.path.splitext(file)[0].rstrip("LN")
                with open(os.path.join(subdir, file), encoding="utf-8") as f:
                    content = f.read()
                    # let's find something like "(013032)電子工程學系(甲組)"
                    founds = re.finditer(r"\(([0-9]{6})\)\s*([\w\s\[\]［］()（）]+)", content)
                    for found in founds:
                        departmentMap[found.group(1)] = found.group(2).strip()
                    # let's find something like "10008031" (學測准考證號)
                    founds = re.finditer(r"\b([0-9]{8})\b", content)
                    for found in founds:
                        if departmentId not in departmentToAdmittees:
                            departmentToAdmittees[departmentId] = []
                        departmentToAdmittees[departmentId].append(found.group(1))

        print("[crawler_caac] DB Gen: filling data into the DB file.")

        # generate db
        if os.path.isfile(dbFilepath):
            os.remove(dbFilepath)

        conn = sqlite3.connect(dbFilepath)

        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS universities (
                    id      CHAR(3)     PRIMARY KEY    NOT NULL,
                    name    CHAR(50)                   NOT NULL
                );
            """
        )
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS departments (
                    id     CHAR(6)      PRIMARY KEY    NOT NULL,
                    name   CHAR(100)                   NOT NULL
                );
            """
        )
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS qualified (
                    departmentId    CHAR(6)    NOT NULL,
                    admissionId     CHAR(8)    NOT NULL,
                    FOREIGN KEY(departmentId) REFERENCES departments(id)
                );
            """
        )
        conn.execute(
            """
                CREATE INDEX IF NOT EXISTS admissionId_index
                ON qualified (admissionId);
            """
        )

        # insert data into db
        conn.executemany(
            """
                INSERT INTO universities (id, name)
                VALUES (?, ?);
            """,
            universityMap.items(),
        )
        conn.executemany(
            """
                INSERT INTO departments (id, name)
                VALUES (?, ?);
            """,
            departmentMap.items(),
        )
        for departmentId, admissionIds in departmentToAdmittees.items():
            conn.executemany(
                """
                    INSERT INTO qualified (departmentId, admissionId)
                    VALUES (?, ?);
                """,
                zip([departmentId] * len(admissionIds), admissionIds),
            )

        conn.commit()
        conn.close()

        print("[crawler_caac] DB Gen: done.")

    @classmethod
    def getPage(cls, url: str, retry_s: float = 3.0) -> str | None:
        """get a certain web page"""

        while True:
            # try to get page content
            try:
                scraper = cloudscraper.create_scraper(delay=None, interpreter="js2py", allow_brotli=True, debug=False)

                return scraper.get(url).content.decode("utf-8")
            # somehow we cannot get the page content
            except Exception as e:
                errMsg = str(e)
                print(errMsg)

                # HTTP error code
                if errMsg.startswith("HTTP Error "):
                    return None

            # fail to fetch the page, let's sleep for a while
            time.sleep(retry_s)

    def writeFile(self, filename: str, content: str = "", mode: str = "w", codec: str = "utf-8") -> None:
        """write content to an external file"""

        # create directory if the directory does exist yet
        filedir = os.path.dirname(filename)
        if filedir and not os.path.isdir(filedir):
            os.makedirs(filedir, exist_ok=True)

        with codecs.open(filename, mode, codec) as f:
            f.write(content)

    def simplifyUrl(self, url: str) -> str:
        url = re.sub(r"(^|/)./", r"\1", url)
        url = re.sub(r"(?<!:)/{2,}", r"/", url)

        return url
