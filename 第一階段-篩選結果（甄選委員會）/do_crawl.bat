@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply109/109apply_6pSieveXw_ju9sd98/html_sieve_109pgx3/ColPost/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
