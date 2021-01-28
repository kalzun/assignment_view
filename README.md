# Steps to install in local virtual environment
Clone the repository:  
`git clone <url>`

Make a virtualenvironment, enter directory and activate the virtualenvironment:  
`virtualenv assignment_view`  
`cd assignment_view`  
`source bin/activate`  

Install requirements:  
`pip install -r requirements.txt`  

Export groups from Canvas (this you only need once pr semester):
![export_groups](app/demo/export_groups.png)

Download submissions from Canvas:
![download_submissions](app/demo/download_submissions.png)

Copy CSV and ZIP to zips folder in the app-directory:
![csv_zip_to_folder](app/demo/csv_zip_to_folder.png)

Make sure `semester.json` is setup to the correct coursecode and number of groups.  

Now you should be able to run the program with:  
`./run.sh`  

