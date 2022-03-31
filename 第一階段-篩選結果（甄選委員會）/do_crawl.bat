@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply111/111apply_kSieveOD_8w4Qas6g/html_sieve_111psHkq5/ColPost/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
