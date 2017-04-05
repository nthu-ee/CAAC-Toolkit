@ECHO OFF

REM The department ID of NTHU EE "Jia" Group
SET department_A=011322
REM The department ID of NTHU EE "Yi" Group
SET department_B=011332

python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-A.csv" --departmentIds=%department_A%
python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-B.csv" --departmentIds=%department_B%
python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-AB.csv" --departmentIds=%department_A%,%department_B%

PAUSE
