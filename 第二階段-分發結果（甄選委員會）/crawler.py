from __future__ import annotations

import argparse
import os
import sys
import re
import time

from loguru import logger

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from caac_package.crawler import Crawler

def extract_year_from_url(url: str) -> int:
    """
    從 CAAC 的網址中提取西元年。
    ex: https://.../apply113/... → 2024 (113 年)
    """
    match = re.search(r"/apply(\d{3})/", url)
    if not match:
        logger.error(f"無法從 URL 提取年份：{url}")
        raise ValueError("URL 中找不到年份資訊")

    tw_year_abbreviated = int(match.group(1))
    logger.info(f"從 URL 提取年份：民國 {tw_year_abbreviated} 年")
    return tw_year_abbreviated


parser = argparse.ArgumentParser(description="A Crawler for CAAC website.")
parser.add_argument(
    "--project-index-url",
    type=str,
    default="",
    help="The index URL of the CAAC HTML page.",
)
args = parser.parse_args()

try:
    year = extract_year_from_url(args.project_index_url)
except ValueError as e:
    logger.error(str(e))
    sys.exit(1)

t_start = time.time()

crawler = Crawler(year, "apply_entrance", args.project_index_url)
crawler.run(show_message=True)

t_end = time.time()

logger.info(f"[Done] It takes {t_end - t_start} seconds.")
