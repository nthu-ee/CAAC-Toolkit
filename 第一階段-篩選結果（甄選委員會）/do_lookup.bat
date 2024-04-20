@echo off

rem The department ID of NTHU EE "Jia" Group
set department_nthuee_jia=011312
rem The department ID of NTHU EE "Yi" Group
set department_nthuee_yi=011322

python lookup.py --output-format="nthu_ee" --output="NTHU-EE-A.xlsx" --department-ids="%department_nthuee_jia%"
python lookup.py --output-format="nthu_ee" --output="NTHU-EE-B.xlsx" --department-ids="%department_nthuee_yi%"
python lookup.py --output-format="nthu_ee" --output="NTHU-EE-AB.xlsx" --department-ids="%department_nthuee_jia%,%department_nthuee_yi%"

pause
