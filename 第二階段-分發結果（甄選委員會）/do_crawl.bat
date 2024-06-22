@echo off

rem The (base) URL of the CAAC HTML page
set project_index_url="https://www.cac.edu.tw/CacLink/apply113/113appLy_F3gh9Yd_EntraNce_D95pE3ta/html_entrance_77Gf9Kw2/result_html/result_apply/collegeList.htm"

python crawler.py --project-index-url="%project_index_url%"

pause
