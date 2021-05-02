#!/usr/bin/env bash
# if [[ "$OSTYPE" == "msys" ]]; then
#     set
python -c "import webbrowser as wb; wb.open('localhost:5000')" & flask run
