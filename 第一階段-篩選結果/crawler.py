import argparse
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from caac_package.Crawler import Crawler
from caac_package.Year import Year

parser = argparse.ArgumentParser(description="A Crawler for CAAC website.")
parser.add_argument(
    "--year",
    type=int,
    default=Year.YEAR_CURRENT,
    help="The year of data to be processed. (ex: 2017 or 106 is the same)",
)
# fmt: off
parser.add_argument(
    "--projectBaseUrl",
    type=str,
    default="",
    help="The (base) URL of the CAAC HTML page.",
)
# fmt: on
args = parser.parse_args()

year = Year.taiwanize(args.year)

t_start = time.time()

crawler = Crawler(year, args.projectBaseUrl)
crawler.run()

t_end = time.time()

print("[Done] It takes {} seconds.".format(t_end - t_start))
