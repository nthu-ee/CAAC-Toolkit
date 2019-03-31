from .ProjectConfig import ProjectConfig
from pyquery import PyQuery as pq
import codecs
import lxml
import os
import re
import sqlite3
import time
import urllib


class Crawler():

    year = 0
    projectBaseUrl = ''

    collegeListUrl = ''
    resultDir = ''

    def __init__(self, year, projectBaseUrl = ''):
        self.year = year
        self.resultDir = ProjectConfig.CRAWLER_RESULT_DIR.format(self.year)

        #----------------#
        # projectBaseUrl #
        #----------------#
        self.projectBaseUrl = projectBaseUrl.strip()

        if re.search(r"\.[a-zA-Z0-9_]+$", self.projectBaseUrl):
            self.projectBaseUrl = os.path.dirname(self.projectBaseUrl)

        # ensure trailing backslash
        self.projectBaseUrl = self.projectBaseUrl.rstrip('/') + '/'

        self.projectBaseUrl = self.projectBaseUrl.format(self.year)

        #----------------#
        # collegeListUrl #
        #----------------#
        self.collegeListUrl = self.projectBaseUrl + 'collegeList.htm'

    def run(self):
        # prepare the result directory
        os.makedirs(self.resultDir, exist_ok=True)

        filepaths = self.fetchAndSaveCollegeList()
        filepaths = self.fetchAndSaveDepartmentLists(filepaths)
        self.fetchAndSaveDepartmentApplys(filepaths)
        self.generateDb()

    def fetchAndSaveCollegeList(self):
        departmentLists = []

        # the user may give a wrong URL in the last run
        # in that case, we overwrite the old file and run again
        try:
            content = self.fetchAndSavePage(self.collegeListUrl, overwrite=False, log=True)
            links = pq(content)('a')
        except lxml.etree.ParserError:
            content = self.fetchAndSavePage(self.collegeListUrl, overwrite=True, log=True)
            links = pq(content)('a')

        for link in links.items():
            href = link.attr('href')
            if 'common/' in href or 'extra/' in href:
                departmentLists.append(href)

        return departmentLists

    def fetchAndSaveDepartmentLists(self, filepaths):
        departmentApplys = []

        for filepath in filepaths:
            content = self.fetchAndSavePage(self.projectBaseUrl + filepath, overwrite=False, log=True)
            links = pq(content)('a')
            for link in links.items():
                href = link.attr('href')
                if 'apply/' in href:
                    for prefix in [ 'common/', 'extra/' ]:
                        if prefix in filepath:
                            departmentApplys.append(self.simplifyUrl(prefix + href))
                            break

        return departmentApplys

    def fetchAndSaveDepartmentApplys(self, filepaths):
        for filepath in filepaths:
            self.fetchAndSavePage(self.projectBaseUrl + filepath, overwrite=False, log=True)

        print('[crawler_caac] Finish crawling.')

    def fetchAndSavePage(self, url, overwrite=True, log=False):
        """ fetch and save a page depending on its URL """

        filepath = url.replace(self.projectBaseUrl, '')
        filepathAbsolute = os.path.join(self.resultDir, filepath)
        if not overwrite and os.path.isfile(filepathAbsolute):
            with open(filepathAbsolute, 'r', encoding='utf-8') as f:
                if log is True:
                    print('[Local] ' + url)
                return f.read()

        if log is True:
            print('[Fetch] ' + url)

        content = self.getPage(url)
        self.writeFile(filepathAbsolute, content)
        return content

    def generateDb(self):
        """ generate a db file from crawled html files """

        print('[crawler_caac] Generating DB file...')

        dbFilepath = ProjectConfig.getCrawledDbFilepath(self.year)

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

        # build universityMap
        with open(os.path.join(self.resultDir, 'collegeList.htm'), 'r', encoding='utf-8') as f:
            content = f.read()
            founds = re.finditer(r'\(([0-9]{3})\)\d*([\w\s]+)', content)
            for found in founds:
                # let's find something like "(013)國立交通大學"
                universityMap[found.group(1)] = found.group(2).strip()

        # build departmentMap and departmentToAdmittees
        basePath = os.path.join(self.resultDir, 'common', 'apply')
        for subdir, dirs, files in os.walk(basePath):
            for file in files:
                departmentId = os.path.splitext(file)[0]
                with open(os.path.join(basePath, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # let's find something like "(013032)電子工程學系(甲組)"
                    founds = re.finditer(r'\(([0-9]{6})\)\s*([\w\s\[\]［］()（）]+)', content)
                    for found in founds:
                        departmentMap[found.group(1)] = found.group(2).strip()
                    # let's find something like "10008031" (學測准考證號)
                    founds = re.finditer(r'\b([0-9]{8})\b', content)
                    for found in founds:
                        if departmentId not in departmentToAdmittees:
                            departmentToAdmittees[departmentId] = []
                        departmentToAdmittees[departmentId].append(found.group(1))
            break

        # generate db
        if os.path.isfile(dbFilepath):
            os.remove(dbFilepath)

        conn = sqlite3.connect(dbFilepath)

        conn.execute('''
            CREATE TABLE IF NOT EXISTS universities (
                id      CHAR(3)     PRIMARY KEY    NOT NULL,
                name    CHAR(50)                   NOT NULL
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id     CHAR(6)      PRIMARY KEY    NOT NULL,
                name   CHAR(100)                   NOT NULL
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS qualified (
                departmentId    CHAR(6)    NOT NULL,
                admissionId     CHAR(8)    NOT NULL
            );
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS admissionId_index
            ON qualified (admissionId);
        ''')

        # insert data into db
        for universityId, universityName in universityMap.items():
            conn.execute('''
                INSERT INTO universities (id, name)
                VALUES (?, ?)
            ''', (universityId, universityName,))
        for departmentId, departmentName in departmentMap.items():
            conn.execute('''
                INSERT INTO departments (id, name)
                VALUES (?, ?)
            ''', (departmentId, departmentName,))
        for departmentId, admissionIds in departmentToAdmittees.items():
            for admissionId in admissionIds:
                conn.execute('''
                    INSERT INTO qualified (departmentId, admissionId)
                    VALUES (?, ?)
                ''', (departmentId, admissionId,))

        conn.commit()
        conn.close()

        print('[crawler_caac] DB file is successfully generated.')

    def getPage(self, *args):
        """ get a certain web page """

        while True:
            # try to get page content
            try:
                url = args[0]
                urlParsed = urllib.parse.urlparse(url)
                req = urllib.request.Request(*args, headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Encoding': 'deflate',
                    'Accept-Language': 'zh-TW,zh;q=0.8,en-US;q=0.6,en;q=0.4',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36',
                    'Host': urlParsed.netloc,
                    'Referer': '{uri.scheme}://{uri.netloc}'.format(uri=urlParsed),
                })
                with urllib.request.urlopen(req) as resp:
                    return resp.read().decode('utf-8')
            # somehow we cannot get the page content
            except Exception as e:
                errMsg = str(e)
                # HTTP error code
                if errMsg.startswith('HTTP Error '):
                    return None

            # fail to fetch the page, let's sleep for a while
            time.sleep(1)

    def writeFile(self, filename, content='', mode='w', codec='utf-8'):
        """ write content to an external file """

        # create directory if the directory does exist yet
        filedir = os.path.dirname(filename)
        if filedir and not os.path.isdir(filedir):
            os.makedirs(filedir, exist_ok=True)

        with codecs.open(filename, mode, codec) as f:
            f.write(content)

    def simplifyUrl(self, url):
        url = re.sub(r'(^|/)./', r'\1', url)
        url = re.sub(r'(?<!:)/{2,}', r'/', url)
        return url
