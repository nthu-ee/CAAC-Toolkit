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
    rootPageUrl = ''

    projectBaseUrl = ''
    collegeListUrl = ''
    resultDir = ''

    def __init__(self, year):
        self.year = year
        self.baseUrl = self.baseUrl_f.format(year)
        self.rootPageUrl = self.baseUrl + 'result.php'
        self.resultDir = 'crawler_' + self.year

    def run(self):
        # prepare the result directory
        os.makedirs(self.resultDir, exist_ok=True)

        self.processCollegeListUrl()
        filepaths = self.fetchAndSaveCollegeList()
        filepaths = self.fetchAndSaveDepartmentLists(filepaths)
        self.fetchAndSaveDepartmentApplys(filepaths)
        self.generateDb()

    def processCollegeListUrl(self):
        """ get the URL of 大學個人申請入學招生 第一階段篩選結果 """

        url = self.baseUrl + 'result.php'
        content = self.getPage(url)

        if content is None:
            raise Exception('Fail to find /ColPost/collegeList.htm from {}'.format(self.rootPageUrl))
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

    def fetchAndSavePage(self, url, log=False):
        if log is True:
            print('[Fetching] ' + url)
        content = self.getPage(url)
        filepath = url.replace(self.projectBaseUrl, '')
        self.writeFile(os.path.join(self.resultDir, filepath), content)
        return content

    def generateDb(self):
        pass

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
