from __future__ import annotations

import sys
from pathlib import Path

from .year import Year


def get_script_dir() -> Path:
    # @see https://pythonhosted.org/PyInstaller/runtime-information.html
    # we are running in a bundle
    if getattr(sys, "frozen", False):
        # we are running in a one-file bundle
        if getattr(sys, "executable", ""):
            return Path(sys.executable).resolve().parent
        # we are running in a one-folder bundle
        if MEIPASS := getattr(sys, "_MEIPASS"):
            return Path(MEIPASS)
        raise RuntimeError("Cannot determine the script directory.")
    # we are running in a normal Python environment
    return Path(__file__).resolve().parent


class ProjectConfig:
    # followings are adjust-able
    ROOT_DIR = get_script_dir().parent
    DATA_DIR = ROOT_DIR / "data"
    CRAWLER_WORKER_NUM = 8
    CRAWLED_DB_FILENAME = "sqlite3.db"

    @classmethod
    def get_crawled_result_dir(cls, year: int, apply_stage: str) -> Path:
        """Get the crawled result directory for a sepecific year/stage."""
        year = Year.taiwanize(year)
        return cls.DATA_DIR / f"crawler_{year}/stage_{apply_stage}"

    @classmethod
    def get_crawled_db_file(cls, year: int, apply_stage: str) -> Path:
        """Get the crawled db file for a sepecific year/stage."""
        year = Year.taiwanize(year)
        return cls.get_crawled_result_dir(year, apply_stage) / cls.CRAWLED_DB_FILENAME
