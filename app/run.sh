#!/usr/bin/env bash
python group_sorter.py && python -c "import webbrowser as wb; wb.open('localhost:5000')" & flask run 
