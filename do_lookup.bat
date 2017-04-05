@ECHO OFF

REM 清華大學 電機系 甲組 的 系所編號
SET department_A=011322
REM 清華大學 電機系 乙組 的 系所編號
SET department_B=011332

python lookup.py --departmentIds=%department_A% --output="NTHU-EE-A.csv"
python lookup.py --departmentIds=%department_B% --output="NTHU-EE-B.csv"
python lookup.py --departmentIds=%department_A%,%department_B% --output="NTHU-EE-AB.csv"

PAUSE
