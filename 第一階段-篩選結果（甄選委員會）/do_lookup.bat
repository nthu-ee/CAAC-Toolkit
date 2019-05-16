@ECHO OFF

REM The department ID of NTHU EE "Jia" Group
SET department_NthuEe_Jia=011332
REM The department ID of NTHU EE "Yi" Group
SET department_NthuEe_Yi=011342

python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-A.xlsx" --departmentIds="%department_NthuEe_Jia%"
python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-B.xlsx" --departmentIds="%department_NthuEe_Yi%"
python lookup.py --outputFormat="NthuEe" --output="NTHU-EE-AB.xlsx" --departmentIds="%department_NthuEe_Jia%,%department_NthuEe_Yi%"

PAUSE
