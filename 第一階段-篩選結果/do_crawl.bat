@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.caac.ccu.edu.tw/CacLink/apply107/107apply_Sieve_pg58e3q/html_sieve_107yaya/ColPost/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
