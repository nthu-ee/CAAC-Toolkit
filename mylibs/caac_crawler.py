from pyquery import PyQuery as pq
import codecs
import os
import re
import sqlite3
import time
import urllib


class caac_crawler():

    year = 0
    baseUrl = ''
    baseUrl_f = 'https://www.caac.ccu.edu.tw/caac{}/'

    projectBaseUrl = ''
    collegeListUrl = ''
    resultDir = ''

    def __init__(self, year):
        self.year = year
        self.baseUrl = self.baseUrl_f.format(year)
        self.resultDir = 'crawler_{}'.format(self.year)

    def run(self):
        # prepare the result directory
        os.makedirs(self.resultDir, exist_ok=True)

        self.processCollegeListUrl()
        filepaths = self.fetchAndSaveCollegeList()
        filepaths = self.fetchAndSaveDepartmentLists(filepaths)
        self.fetchAndSaveDepartmentApplys(filepaths)
        self.generateDb()

    def processCollegeListUrl(self):
        """ set the URL of 大學個人申請入學招生 第一階段篩選結果 """

        url = self.baseUrl + 'result.php'
        content = self.getPage(url)

        if content is None:
            raise Exception('Fail to find /ColPost/collegeList.htm from {}'.format(url))
        else:
            links = pq(content)('a')
            for link in links.items():
                href = link.attr('href')
                if '/ColPost/collegeList.htm' in href:
                    if self.isUrl(href):
                        self.collegeListUrl = href
                    else:
                        self.collegeListUrl = self.simplifyUrl(self.baseUrl + href)
                    self.projectBaseUrl = self.collegeListUrl[:-len('/collegeList.htm')+1]

    def fetchAndSaveCollegeList(self):
        departmentLists = []

        content = self.fetchAndSavePage(self.collegeListUrl, log=True)
        links = pq(content)('a')

        for link in links.items():
            href = link.attr('href')
            if 'common/' in href or 'extra/' in href:
                departmentLists.append(href)

        return departmentLists

    def fetchAndSaveDepartmentLists(self, filepaths):
        departmentApplys = []

        for filepath in filepaths:
            content = self.fetchAndSavePage(self.projectBaseUrl + filepath, log=True)
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
            self.fetchAndSavePage(self.projectBaseUrl + filepath, log=True)

        print('[caac_crawler] Finish crawling.')

    def fetchAndSavePage(self, url, log=False):
        """ fetch and save a page depending on its URL """

        if log is True:
            print('[Fetching] ' + url)
        content = self.getPage(url)
        filepath = url.replace(self.projectBaseUrl, '')
        self.writeFile(os.path.join(self.resultDir, filepath), content)
        return content

    def generateDb(self):
        """ generate a db file from crawled html files """

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
                # let's find something like "(001)國立臺灣大學"
                universityMap[found.group(1)] = found.group(2).strip()

        # build departmentMap and departmentToAdmittees
        basePath = os.path.join(self.resultDir, 'common', 'apply')
        for subdir, dirs, files in os.walk(basePath):
            for file in files:
                departmentId = os.path.splitext(file)[0]
                with open(os.path.join(basePath, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    # let's find something like "(001012)中國文學系"
                    founds = re.finditer(r'\(([0-9]{6})\)\d*([\w\s]+)', content)
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
        dbFilepath = os.path.join(self.resultDir, 'sqlite3.db')

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

        print('[caac_crawler] DB file is successfully generated.')

    def getPage(self, *args):
        """ get a certain web page """

        while True:
            # try to get page content
            try:
                req = urllib.request.Request(*args)
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

    def isUrl(self, url):
        return '://' in url

    def simplifyUrl(self, url):
        url = re.sub(r'(^|/)./', r'\1', url)
        url = re.sub(r'(?<!:)/{2,}', r'/', url)
        return url
