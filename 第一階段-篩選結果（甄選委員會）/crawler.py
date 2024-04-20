from __future__ import annotations

import argparse
import os
import sys
import time

from loguru import logger

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from caac_package.crawler import Crawler
from caac_package.year import Year

parser = argparse.ArgumentParser(description="A Crawler for CAAC website.")
parser.add_argument(
    "--year",
    type=int,
    default=Year.YEAR_CURRENT,
    help="The year of data to be processed. (ex: 2017 or 106 is the same)",
)
parser.add_argument(
    "--project-index-url",
    type=str,
    default="",
    help="The index URL of the CAAC HTML page.",
)
args = parser.parse_args()

year = Year.taiwanize(args.year)

t_start = time.time()

crawler = Crawler(year, "apply_sieve", args.project_index_url)
crawler.run(show_message=True)

t_end = time.time()

logger.info(f"[Done] It takes {t_end - t_start} seconds.")
