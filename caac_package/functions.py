from __future__ import annotations

import base64
import os
import re
from collections import ChainMap
from collections.abc import Generator, Iterable
from io import BytesIO
from pathlib import Path
from typing import Any, TypeVar

import pytesseract
from loguru import logger
from PIL import Image
from pyquery import PyQuery as pq

T = TypeVar("T")


def data_uri_to_image(data_uri: str) -> Image.Image:
    base64_data = re.sub(r"^data:image/[^;]+;base64,", "", data_uri)
    byte_data = base64.b64decode(base64_data)
    return Image.open(BytesIO(byte_data))


def ocr_data_uri(data_uri: str) -> str:
    # ensure that tesseract.exe is in PATH
    extra_paths: list[str] = [
        # R"C:\Program Files\Tesseract-OCR",
        # R"C:\Program Files (x86)\Tesseract-OCR",
        str(get_tesseract_dir()),
    ]
    os.environ["PATH"] = os.pathsep.join(
        ChainMap(
            {path: True for path in os.environ["PATH"].split(os.pathsep)},
            {path: True for path in extra_paths},
        ).keys()
    )

    img = data_uri_to_image(data_uri)
    result = pytesseract.image_to_string(img)
    img.close()

    return result


def get_tesseract_dir() -> Path:
    from caac_package.project_config import ProjectConfig

    return ProjectConfig.ROOT_DIR / "bin/tesseract-ocr"


def get_chromium_dir() -> Path:
    from caac_package.project_config import ProjectConfig

    return ProjectConfig.ROOT_DIR / "bin/chromium"


def get_chromium_binary_path() -> Path:
    return get_chromium_dir() / "bin/chrome.exe"


def get_chromium_profile_dir() -> Path:
    return get_chromium_dir() / "profile"


def parse_www_com_tw(content: str = "") -> dict[str, Any]:
    people_result: dict[str, Any] = {
        # '准考證號': {
        #     '_name': '考生姓名',
        #     '系所編號1': {
        #         '_name': '國立臺灣大學醫學系(繁星第八類)',
        #         'is_dispatched': False,
        #         'apply_state': 'primary',
        #     }
        #     ...
        # },
        # ...
    }

    admission_id_regex = re.compile(r"\b(\d{8})\b")
    department_id_regex = re.compile(r"_(\d{6,7})_")

    # sanitization
    content = content.replace("\r", "").replace("\n", " ")
    # get the result html table
    person_rows = pq(content)("#mainContent > table:first > tbody > tr")

    for person_row in person_rows.items():
        html = person_row.outer_html()

        if not (matches := re.search(r'data:image/[^;]+;base64,[^\'"]*', str(html))):
            continue

        admission_id = ocr_data_uri(matches.group(0))
        # simple sanitization...
        admission_id = re.sub(r"[^0-9a-zA-Z]+", "", admission_id)

        if not admission_id_regex.match(admission_id):
            logger.error(f"Wrong admission ID: {admission_id}")
            continue

        person_name = str(person_row("td:nth-child(4)").text()).strip()
        person_result: dict[str, dict[str, Any]] = {admission_id: {"_name": person_name}}

        apply_table_rows = person_row("td:nth-child(5) table:first > tbody > tr")
        for apply_table_row in apply_table_rows.items():
            if not (find_department_id := department_id_regex.search(str(apply_table_row.outer_html()))):
                continue

            department_id = str(find_department_id.group(1))
            department_name = str(apply_table_row("td:nth-child(2)").text()).strip()
            apply_state = str(apply_table_row("td:nth-child(3)").text()).strip()

            person_result[admission_id][department_id] = {
                "_name": department_name,
                "is_dispatched": "分發錄取" in str(apply_table_row.outer_html()),
                "apply_state": normalize_apply_state_c2e(apply_state),
            }

        logger.info(f"Parsed data: {person_result}")

        people_result.update(person_result)

    return people_result


def normalize_apply_state_c2e(chinese: str) -> str:
    # 正取
    if "正" in chinese:
        order = re.search(r"(\d+)", chinese)
        order = order.group(1) if order else "?"
        return f"primary-{order}"
    # 備取
    if "備" in chinese:
        order = re.search(r"(\d+)", chinese)
        order = order.group(1) if order else "?"
        return f"spare-{order}"
    # 落榜
    if "落" in chinese:
        return "failed"
    # 未知（無資料）
    return "unknown"


def normalize_apply_state_e2c(english: str) -> str:
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


def can_be_int(s: Any) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def unique(items: Iterable[T], *, clear: bool = False) -> Generator[T, None, None]:
    tmp = {item: True for item in items}
    items_it = tmp.keys()
    if clear:
        items_it = filter(None, items_it)
    yield from items_it
