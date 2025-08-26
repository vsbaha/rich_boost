@echo off
set /p msg="Введите комментарий к коммиту: "
git add .
git commit -m "%msg%"
git push
pause
