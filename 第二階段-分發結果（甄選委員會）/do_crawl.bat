@echo off

rem The (base) URL of the CAAC HTML page
set project_index_url="https://www.cac.edu.tw/CacLink/apply109/109apply_cP5_Entrance_r6f57a5Fm/html_entrance_5R109hlw/result_html/result_apply/collegeList.htm"

python crawler.py --project-index-url="%project_index_url%"

pause
