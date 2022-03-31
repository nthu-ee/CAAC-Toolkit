from io import BytesIO
from PIL import Image
from pyquery import PyQuery as pq
from typing import Any, Dict, List, Tuple, TypeVar
import base64
import os
import pytesseract
import re
import sqlite3

T = TypeVar("T")


def data_uri_to_image(data_uri: str) -> Image.Image:
    base64_data = re.sub(r"^data:image/[^;]+;base64,", "", data_uri)
    byte_data = base64.b64decode(base64_data)
    image_data = BytesIO(byte_data)

    return Image.open(image_data)


def ocr_data_uri(data_uri: str) -> str:
    # ensure that tesseract.exe is in PATH
    paths = [
        # r"C:\Program Files\Tesseract-OCR",
        # r"C:\Program Files (x86)\Tesseract-OCR",
        get_tesseract_dir(),
    ]
    for path in paths:
        if path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + path

    img = data_uri_to_image(data_uri)
    result = pytesseract.image_to_string(img)
    img.close()

    return result


def get_tesseract_dir() -> str:
    from caac_package.ProjectConfig import ProjectConfig

    return os.path.join(ProjectConfig.ROOT_DIR, "bin", "tesseract-ocr")


def get_chromium_dir() -> str:
    from caac_package.ProjectConfig import ProjectConfig

    return os.path.join(ProjectConfig.ROOT_DIR, "bin", "chromium")


def get_chromium_binary_path() -> str:
    return os.path.join(get_chromium_dir(), "bin", "chrome.exe")


def get_chromium_profile_dir() -> str:
    return os.path.join(get_chromium_dir(), "profile")


def loadDb(dbFilepath: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    if not os.path.isfile(dbFilepath):
        raise Exception(f"DB file does not exist: {dbFilepath}")

    # connect to db file
    with sqlite3.connect(dbFilepath) as conn:

        # build universityMap
        cursor = conn.execute(
            """
                SELECT id, name
                FROM universities
            """
        )
        universityMap: Dict[str, str] = {university[0]: university[1] for university in cursor.fetchall()}

        # build departmentMap
        cursor = conn.execute(
            """
                SELECT id, name
                FROM departments
            """
        )

        departmentMap: Dict[str, str] = {department[0]: department[1] for department in cursor.fetchall()}

    return universityMap, departmentMap


def parseWwwComTw(content: str = "") -> Dict[str, Any]:
    peopleResult = {
        # '准考證號': {
        #     '_name': '考生姓名',
        #     '系所編號1': {
        #         '_name': '國立臺灣大學醫學系(繁星第八類)',
        #         'isDispatched': False,
        #         'applyState': 'primary',
        #     }
        #     ...
        # },
        # ...
    }

    admissionIdRegex = r"\b(\d{8})\b"
    departmentIdRegex = r"_(\d{6,7})_"

    # sanitization
    content = content.replace("\r", "").replace("\n", " ")
    # get the result html table
    personRows = pq(content)("#mainContent table:first > tbody > tr")

    for personRow in personRows.items():
        html = personRow.html()

        matches = re.search(r'data:image/[^;]+;base64,[^\'"]*', html)
        if not matches:
            continue

        admissionId = ocr_data_uri(matches.group(0))
        # simple sanitization...
        admissionId = re.sub(r"[^0-9a-zA-Z]+", "", admissionId)

        if not re.match(admissionIdRegex, admissionId):
            print(f"Wrong admission ID: {admissionId}")
            continue

        personName = personRow("td:nth-child(4)").text().strip()
        personResult = {admissionId: {"_name": personName}}

        applyTableRows = personRow("td:nth-child(5) table:first > tbody > tr")

        for applyTableRow in applyTableRows.items():
            findDepartmentId = re.search(departmentIdRegex, applyTableRow.html())

            if findDepartmentId is None:
                continue

            departmentId = findDepartmentId.group(1)
            departmentName = applyTableRow("td:nth-child(2)").text().strip()
            applyState = applyTableRow("td:nth-child(3)").text().strip()

            personResult[admissionId][departmentId] = {
                "_name": departmentName,
                "isDispatched": "分發錄取" in applyTableRow.html(),
                "applyState": normalizeApplyStateC2E(applyState),
            }

        print(f"Parsed data: {personResult}\n")

        peopleResult.update(personResult)

    return peopleResult


def normalizeApplyStateC2E(chinese: str) -> str:
    # 正取
    if "正" in chinese:
        order = re.search(r"(\d+)", chinese)
        order = "?" if order is None else order.group(1)
        return f"primary-{order}"
    # 備取
    if "備" in chinese:
        order = re.search(r"(\d+)", chinese)
        order = "?" if order is None else order.group(1)
        return f"spare-{order}"
    # 落榜
    if "落" in chinese:
        return "failed"
    # 未知（無資料）
    return "unknown"


def normalizeApplyStateE2C(english: str) -> str:
    # 正取
    if "primary" in english:
        state = english.split("-")
        if state[1] == "?":
            state[1] = ""
        return f"正{state[1]}"
    # 備取
    if "spare" in english:
        state = english.split("-")
        if state[1] == "?":
            state[1] = ""
        return f"備{state[1]}"
    # 落榜
    if "failed" == english:
        return "落"
    # 尚未放榜
    if "notYet" == english:
        return "未放榜"
    # WTF?
    return "不明"


def canBeInt(s: Any) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def listUnique(theList: List[T], clear: bool = False) -> List[T]:
    theList = list(set(theList))

    return list(filter(None, theList)) if clear else theList
