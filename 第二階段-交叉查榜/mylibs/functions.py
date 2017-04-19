from pyquery import PyQuery as pq
import os
import re
import sqlite3
import time
import urllib


def loadDb(dbFilepath):
    db = {
        'universityMap': {},
        'departmentMap': {},
    }

    # connect to db file
    if not os.path.isfile(dbFilepath):
        raise Exception('DB file does not exist: {}'.format(dbFilepath))

    conn = sqlite3.connect(dbFilepath)

    # build universityMap
    cursor = conn.execute('''
        SELECT id, name
        FROM universities
    ''')
    for university in cursor.fetchall():
        db['universityMap'][university[0]] = university[1]

    # build departmentMap
    cursor = conn.execute('''
        SELECT id, name
        FROM departments
    ''')
    for department in cursor.fetchall():
        db['departmentMap'][department[0]] = department[1]

    conn.close()

    return db


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


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
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.68 Safari/537.36',
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
    peopleResults = {
        # '准考證號': {
        #     '系所編號': 'primary',
        #     ...
        # },
        # ...
    }

    content = content.replace('\r', '').replace('\n', '') # sanitization
    table = pq(content)('#cross_dept tbody') # get the result html table
    rows = table('tr')

    personResult = {}
    for tr in rows.items():
        findAdmissionId = re.search(r'\b[0-9]{8}\b', tr.html())
        isFirstRow = findAdmissionId is not None
        if isFirstRow:
            peopleResults.update(personResult)
            admissionId = findAdmissionId.group(0)
            personResult = {
                admissionId: {},
            }
        department = tr('td a').attr('href').strip('./ ')
        applied = tr('td span').text().strip()
        applied = normalizeApplicationC2E(applied)
        personResult[admissionId][department] = applied
    peopleResults.update(personResult)

    return peopleResults


def normalizeApplicationC2E(chinese):
    # 正取
    if '正' in chinese:
        order = re.search(r'[0-9]+', chinese)
        order = '?' if order is None else order.group(0)
        return 'primary-{}'.format(order)
    # 備取
    if '備' in chinese:
        order = re.search(r'[0-9]+', chinese)
        order = '?' if order is None else order.group(0)
        return 'spare-{}'.format(order)
    # 尚未放榜
    if '未' in chinese and '放榜' in chinese:
        return 'unannounced'
    # 被刷掉了?
    return 'unapplied'


def normalizeApplicationE2C(english):
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
    # 尚未放榜
    if 'unannounced' == english:
        return '未放榜'
    # 被刷掉了?
    if 'unapplied' == english:
        return '未錄取'
    # WTF?
    return '不明'
