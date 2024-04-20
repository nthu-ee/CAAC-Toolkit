from __future__ import annotations

import os
import sys

from .Year import Year


class ProjectConfig:
    # @see https://pythonhosted.org/PyInstaller/runtime-information.html
    # we are running in a bundle
    if getattr(sys, "frozen", False):
        # we are running in a one-file bundle
        if getattr(sys, "executable", ""):
            __script_dir__ = os.path.dirname(os.path.abspath(sys.executable))
        # we are running in a one-folder bundle
        else:
            __script_dir__ = sys._MEIPASS
    # we are running in a normal Python environment
    else:
        __script_dir__ = os.path.dirname(os.path.abspath(__file__))

    # followings are adjust-able
    ROOT_DIR = os.path.abspath(os.path.join(__script_dir__, ".."))
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    CRAWLER_WORKER_NUM = 4
    CRAWLER_RESULT_DIR = os.path.join(DATA_DIR, "crawler_{}")
    CRAWLED_DB_FILENAME = "sqlite3.db"

    @classmethod
    def getCrawledResultDir(cls, year: int, apply_stage: str) -> str:
        """Get the crawled result directory for a sepecific year/stage."""

        year = Year.taiwanize(year)

        return os.path.join(cls.CRAWLER_RESULT_DIR.format(year), f"stage_{apply_stage}")

    @classmethod
    def getCrawledDbFile(cls, year: int, apply_stage: str) -> str:
        """Get the crawled db file for a sepecific year/stage."""

        year = Year.taiwanize(year)

        return os.path.join(cls.getCrawledResultDir(year, apply_stage), cls.CRAWLED_DB_FILENAME)
