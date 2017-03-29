import os
import sqlite3
import sys
import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'libs'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'mylibs'))
from caac_crawler import caac_crawler

# change the working directory
try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

now = datetime.datetime.now()

# set year
year = 106

crawler = caac_crawler(year).run()
