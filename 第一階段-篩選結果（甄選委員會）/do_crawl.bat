@echo off

rem The (base) URL of the CAAC HTML page
set project_index_url="https://www.cac.edu.tw/CacLink/apply113/113applY_xSievePk4g_T43D54VO_91S/html_sieve_113_Ks7Zx/ColPost/collegeList.htm"

python crawler.py --project-index-url="%project_index_url%"

pause
