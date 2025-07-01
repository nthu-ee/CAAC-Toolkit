from __future__ import annotations

import re
import sqlite3
import time
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cloudscraper
import lxml
import lxml.etree
from loguru import logger
from pyquery import PyQuery as pq

from .project_config import ProjectConfig


class Crawler:
    FAILED_URLS = []

    def __init__(self, year: int, apply_stage: str, project_base_url: str) -> None:
        self.year = year
        self.apply_stage = apply_stage
        self.result_dir = ProjectConfig.get_crawled_result_dir(self.year, self.apply_stage)

        self.project_base_url = self.index_url_to_base_url(project_base_url)
        self.college_list_url = f"{self.project_base_url}collegeList.htm"

    @staticmethod
    def index_url_to_base_url(index_url: str) -> str:
        base_url = index_url.strip()
        """
        Eventually, we have something like the following
        `https://www.cac.edu.tw/CacLink/apply113/113applY_xSievePk4g_T43D54VO_91S/html_sieve_113_Ks7Zx/ColPost/`
        """

        # get the parent of "xxx.html"
        if re.search(r"\.[a-zA-Z0-9_]+$", base_url):
            base_url = base_url.rpartition("/")[0]

        # ensure trailing backslash
        return base_url.rstrip("/") + "/"

    def run(self, show_message: bool = False) -> None:
        # prepare the result directory
        self.result_dir.mkdir(parents=True, exist_ok=True)

        filepaths = self.fetch_and_save_college_list()
        filepaths = self.fetch_and_save_department_lists(filepaths)
        self.fetch_and_save_department_applys(filepaths)

        if Crawler.FAILED_URLS:
            failed_log_path = self.result_dir / "failed_urls.txt"
            with open(failed_log_path, "w", encoding="utf-8") as f:
                for url in Crawler.FAILED_URLS:
                    f.write(url + "\n")
            logger.warning(f"{len(Crawler.FAILED_URLS)} URLs failed completely. Saved to: {failed_log_path}")

        self.generate_db()

        if show_message:
            logger.info(f"Crawled files are stored in: {self.result_dir}")

    def fetch_and_save_college_list(self) -> list[str]:
        department_lists: list[str] = []

        # the user may give a wrong URL in the last run
        # in that case, we overwrite the old file and run again
        try:
            content = self.fetch_and_save_page(self.college_list_url, overwrite=False)
            links = pq(content)("a")
        except lxml.etree.ParserError:
            content = self.fetch_and_save_page(self.college_list_url, overwrite=True)
            links = pq(content)("a")

        for link in links.items():
            href = str(link.attr("href"))
            if href.startswith("web/"):
                department_lists.append(href)

        return department_lists

    def fetch_and_save_department_lists(self, filepaths: Iterable[str]) -> list[str]:
        department_applys: list[str] = []

        def worker_fetch_page(filepath: str) -> None:
            content = self.fetch_and_save_page(f"{self.project_base_url}{filepath}", overwrite=False)
            links = pq(content)("a")
            for link in links.items():
                href = str(link.attr("href"))
                if href.startswith(("common/", "extra/")):
                    department_applys.append(self.simplify_url(f"web/{href}"))

        with ThreadPoolExecutor(max_workers=ProjectConfig.CRAWLER_WORKER_NUM) as executor:
            for filepath in filepaths:
                executor.submit(worker_fetch_page, filepath=filepath)

        return department_applys

    def fetch_and_save_department_applys(self, filepaths: Iterable[str]) -> None:
        def worker_fetch_page(filepath: str) -> None:
            self.fetch_and_save_page(f"{self.project_base_url}{filepath}", overwrite=False)

        with ThreadPoolExecutor(max_workers=ProjectConfig.CRAWLER_WORKER_NUM) as executor:
            for filepath in filepaths:
                executor.submit(worker_fetch_page, filepath=filepath)

        logger.info("Finish crawling.")

    def fetch_and_save_page(self, url: str, overwrite: bool = True) -> str:
        """fetch and save a page depending on its URL"""
        logger.info(f"Fetching URL: {url}")

        filepath = url.replace(self.project_base_url, "")
        filepath_abs = self.result_dir / filepath
        if not overwrite and filepath_abs.is_file():
            logger.info(f"Found and reuse local file: {filepath_abs}")
            with open(filepath_abs, encoding="utf-8") as f:
                return f.read()

        content = self.get_page(url) or ""
        self.write_file(filepath_abs, content)
        return content

    def generate_db(self) -> None:
        """Generate a DB file from crawled html files."""
        db_file = ProjectConfig.get_crawled_db_file(self.year, self.apply_stage)

        university_map: dict[str, str] = {}  # ["001": "國立臺灣大學", ...]
        department_map: dict[str, str] = {}  # ["001012": "中國文學系", ...]
        department_to_admittees: defaultdict[str, list[str]] = defaultdict(list)  # {"001012": ["10006201", ...], ...}

        logger.info("DB Generation: gathering data from the source...")

        # build university_map
        with open(self.result_dir / "collegeList.htm", encoding="utf-8") as f:
            content = f.read()
            for found in re.finditer(r"\(([0-9]{3})\)\d*([\w\s]+)", content):
                # let's find something like "(013)國立交通大學"
                university_map[found.group(1)] = found.group(2).strip()

        # build department_map and department_to_admittees
        for path in self.result_dir.rglob("*"):
            if not (path.is_file() and path.suffix in {".htm", ".html"}):
                continue

            department_id = path.stem
            with open(path, encoding="utf-8") as f:
                content = f.read()
                # let's find something like "(013032)電子工程學系(甲組)"
                for found in re.finditer(r"\(([0-9]{6})\)\s*([\w\s\[\]［］()（）]+)", content):
                    # E.g., the ID of "(013062)資訊工程學系(乙組)［離島外加名額］" is actually "013062L"
                    # So, we can't use `found.group(1)` directly because it doesn't contain the trailing "L".
                    department_map[department_id] = found.group(2).strip()
                # let's find something like "10008031" (學測准考證號)
                for found in re.finditer(r"\b([0-9]{8})\b", content):
                    department_to_admittees[department_id].append(found.group(1))

        logger.info("DB Generation: filling data into the DB file.")

        # generate db
        db_file.unlink(missing_ok=True)

        conn = sqlite3.connect(db_file)

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
                    department_id    CHAR(6)    NOT NULL,
                    admission_id     CHAR(8)    NOT NULL,
                    FOREIGN KEY(department_id) REFERENCES departments(id)
                );
            """
        )
        conn.execute(
            """
                CREATE INDEX IF NOT EXISTS admission_id_index
                ON qualified (admission_id);
            """
        )

        # insert data into db
        conn.executemany(
            """
                INSERT INTO universities (id, name)
                VALUES (?, ?);
            """,
            university_map.items(),
        )
        conn.executemany(
            """
                INSERT INTO departments (id, name)
                VALUES (?, ?);
            """,
            department_map.items(),
        )
        for department_id, admissionIds in department_to_admittees.items():
            conn.executemany(
                """
                    INSERT INTO qualified (department_id, admission_id)
                    VALUES (?, ?);
                """,
                zip([department_id] * len(admissionIds), admissionIds),
            )

        conn.commit()
        conn.close()

        logger.info("DB Generation: done.")

    @classmethod
    def get_page(cls, url: str) -> str | None:
        scraper = cloudscraper.create_scraper(
            interpreter="js2py",
            allow_brotli=True,
            debug=False
        )

        for attempt in range(1, 6):
            try:
                response = scraper.get(url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0 Safari/537.36"
                })
                content = response.content.decode("utf-8", errors="ignore")

                if "<html" not in content.lower():
                    logger.warning(f"Invalid HTML content from {url}")
                    return ""

                return content

            except Exception as e:
                if attempt == 5:
                    logger.error(f"Failed to fetch {url} after {attempt} attempts: {e}")
                    cls.FAILED_URLS.append(url)
                    return None
                sleep_time = min(3 * (2 ** (attempt - 1)), 30)
                logger.info(f"Attempt {attempt} failed for {url}. Retrying in {sleep_time}s: {e}")
                time.sleep(sleep_time)

    def write_file(self, filename: str | Path, content: str = "", *, encoding: str = "utf-8") -> None:
        """Write content to an external file."""
        filename = Path(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(content, encoding=encoding)

    def simplify_url(self, url: str) -> str:
        url = re.sub(r"(^|/)./", r"\1", url)
        url = re.sub(r"(?<!:)/{2,}", r"/", url)
        return url
