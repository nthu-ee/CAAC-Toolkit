@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply108/108apply_kg_Entrance_fq6ryh7/html_entrance_kk108nonp/result_html/result_apply/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
