@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply109/109apply_cP5_Entrance_r6f57a5Fm/html_entrance_5R109hlw/result_html/result_apply/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
