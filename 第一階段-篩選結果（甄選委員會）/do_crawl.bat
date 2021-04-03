@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply110/110apply_pgSieve_22sd8rga/html_sieve_110swk5m/ColPost/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
