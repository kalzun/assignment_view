@ECHO off
set FLASK_APP=sort_server.py
cmd /k "cd /d ..\Scripts & activate & cd /d ..\app & python group_sorter.py & start http://localhost:5000 & flask run"