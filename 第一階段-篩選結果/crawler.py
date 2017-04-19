import argparse
import datetime
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'mylibs'))
from crawler_caac import crawler_caac

YEAR_BEGIN = 1911

# change the working directory
try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

parser = argparse.ArgumentParser(description='A crawler for CAAC website.')
parser.add_argument(
    '--year',
    type=int,
    default=datetime.datetime.now().year - YEAR_BEGIN,
    help='The year of data to be crawled. (ex: 2017 or 106 is the same)',
)
args = parser.parse_args()

year = args.year - YEAR_BEGIN if args.year >= YEAR_BEGIN else args.year

t_start = time.time()

# let's do the job
crawler = crawler_caac(year)
crawler.run()

t_end = time.time()

print('[Done] It takes {} seconds.'.format(t_end - t_start))
