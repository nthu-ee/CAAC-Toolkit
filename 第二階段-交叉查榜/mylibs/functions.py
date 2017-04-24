from pyquery import PyQuery as pq
import os
import re
import sqlite3
import time
import urllib


def loadDb(dbFilepath):
    if not os.path.isfile(dbFilepath):
        raise Exception('DB file does not exist: {}'.format(dbFilepath))

    # connect to db file
    with sqlite3.connect(dbFilepath) as conn:

        # build universityMap
        cursor = conn.execute('''
            SELECT id, name
            FROM universities
        ''')
        universityMap = {
            university[0]: university[1]
            for university in cursor.fetchall()
        }

        # build departmentMap
        cursor = conn.execute('''
            SELECT id, name
            FROM departments
        ''')
        departmentMap = {
            department[0]: department[1]
            for department in cursor.fetchall()
        }

    return universityMap, departmentMap


def batch(iterable, batchSize=1):
    length = len(iterable)
    for idx in range(0, length, batchSize):
        # python will do the boundary check automatically
        yield iterable[idx:idx+batchSize]


def canBeInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def getPage(*args):
    """ get a certain web page """

    while True:
        # try to get page content
        try:
            req = urllib.request.Request(*args, headers={
                # disguise our crawler as Google Chrome
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36',
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


def parseFreshmanTw(content=''):
    peopleResult = {
        # '准考證號': {
        #     '_name': '考生姓名',
        #     '系所編號1': 'primary',
        #     ...
        # },
        # ...
    }

    content = content.replace('\r', '').replace('\n', ' ') # sanitization
    table = pq(content)('#cross_dept tbody') # get the result html table
    rows = table('tr')

    personResult = {}
    for tr in rows.items():
        findAdmissionId = re.search(r'\b(\d{8})\b', tr.text())
        isFirstRow = findAdmissionId is not None
        if isFirstRow:
            peopleResult.update(personResult)
            admissionId = findAdmissionId.group(1)
            personName = tr('td:nth-child(2)').text().strip()
            personResult = {
                admissionId: { '_name': personName },
            }
        department = tr('td a').attr('href').rstrip('/').split('/')[-1].strip()
        applyState = tr('td span').text().strip()
        personResult[admissionId][department] = normalizeApplyStateC2E(applyState)
    peopleResult.update(personResult)

    return peopleResult


def normalizeApplyStateC2E(chinese):
    # 正取
    if '正' in chinese:
        order = re.search(r'(\d+)', chinese)
        order = '?' if order is None else order.group(1)
        return 'primary-{}'.format(order)
    # 備取
    if '備' in chinese:
        order = re.search(r'(\d+)', chinese)
        order = '?' if order is None else order.group(1)
        return 'spare-{}'.format(order)
    # 落榜
    if '落' in chinese or '' == chinese:
        return 'failed'
    # 尚未放榜
    if '未' in chinese and '放' in chinese:
        return 'notYet'
    # WTF?
    return 'unknown'


def normalizeApplyStateE2C(english):
    # 正取
    if 'primary' in english:
        state = english.split('-')
        if state[1] == '?':
            state[1] = ''
        return '正{}'.format(state[1])
    # 備取
    if 'spare' in english:
        state = english.split('-')
        if state[1] == '?':
            state[1] = ''
        return '備{}'.format(state[1])
    # 落榜
    if 'failed' == english:
        return '落'
    # 尚未放榜
    if 'notYet' == english:
        return '未放榜'
    # WTF?
    return '不明'
