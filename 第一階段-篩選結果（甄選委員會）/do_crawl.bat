@ECHO OFF

REM The (base) URL of the CAAC HTML page
SET projectBaseUrl="https://www.cac.edu.tw/CacLink/apply108/108apply_SieveR_erg95fs/html_sieve_coco108/ColPost/collegeList.htm"

python crawler.py --projectBaseUrl="%projectBaseUrl%"

PAUSE
