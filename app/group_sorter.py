from pathlib import Path
from time import time, ctime
from zipfile import ZipFile
import csv
import logging
import shutil
import tempfile


# csvfile = '2020-09-03T1057_Karakterer-INFO132.csv'
# Place the csvfile in the zips_folder

submissions_folder = 'submissions'

positions = {
    'name': 0,
    'usercode': 3,
    'group_info': 4,
}

COURSECODE = 'INFO132'
N_OF_GROUPS = 22
GROUPS = {}

# Logging setup
LOGFOLDER = Path('logs')
LOGFILENAME = 'group_sorter.log'
logging.basicConfig(
                    filename=LOGFOLDER / LOGFILENAME,
                    format='%(levelname)s:%(asctime)s - %(message)s',
                    level=logging.DEBUG,
)
logging.info('Started')

def get_submission_name(zipname: str) -> str:
    '''
    Extract the submission name from the name of the zipfile.
    Regular zipfile-name could be:
    '1599224423_837__INFO132-Temaoppgave_1_submissions.zip'
    [random_number] [coursecode] [submission_name]

    '''
    # If zipname is passed as a stringified path with folder, eg:
    # 'zips/1599224423_837__INFO132-Temaoppgave_1_submissions.zip',
    # this function strips the folders.
    # folder_pos = zipname.rfind('/')
    # zipname = zipname if folder_pos == -1 else zipname[folder_pos+1:]
    start, end = zipname.find(COURSECODE), zipname.find('submissions')
    if start == -1 or end == -1:
        # Did not find what we were after.
        return zipname.rstrip('.zip')
    return zipname[start+len(COURSECODE):end].strip('-').rstrip('_')

def get_zips() -> list:
    app_dir = Path('.')
    files = [str(f) for f in app_dir.glob('*.zip') if COURSECODE in f.name]
    return files


def unzip_file(filename) -> None:
    logging.info(f'Unzipping... ')
    if not Path(filename).exists():
        return False
    with ZipFile(filename, 'r') as zref:
        tmp_dir = tempfile.TemporaryDirectory()
        zref.extractall(tmp_dir.name)
        sort_to_group_folders(tmp_dir.name, filename)
    logging.info(f'Successfully unzipped {filename}')


def sort_to_group_folders(tmpdir_name: str, zipname: str='submission'):
    # Ensure folder structure
    # submission > "Temaoppgave1" > gruppenummer
    submission_name = get_submission_name(zipname)
    root_submission = Path(submissions_folder)
    name_submission = root_submission / Path(submission_name)
    print(f'Extracting: {name_submission}')
    if not root_submission.exists():
        root_submission.mkdir()
    if not name_submission.exists():
        name_submission.mkdir()

    if not GROUPS:
        build_group_overview()
    for n, studentcodes in GROUPS.items():
        to_folder = root_submission / Path(submission_name) / Path(f'{n}')
        if not to_folder.exists():
            to_folder.mkdir()
        for studentcode in studentcodes:
            filepaths = get_path_file_of_student(studentcode, Path(tmpdir_name))
            # Some users have handed in multiple files, be sure to copy them all
            if len(filepaths) == 0:
                continue
                # iterations = len(filepaths)
            for i in range(len(filepaths)):
                folder_file_str = root_submission.name + '/' + filepaths[i].name
                shutil.copy(str(filepaths[i].resolve()), str(to_folder.resolve()))




def copy_files_to_folder(studentcodes: set, group_num: int = 42):
    '''
    Files to be copied to a folder.
    Create folder as child to submissions_folder
    '''
    root_dir = Path('.')
    root_submission = Path(submissions_folder)

    if root_submission.exists():
        to_folder = root_submission / Path(submission_name) / Path(f'{group_num}')
        if not to_folder.exists():
            to_folder.mkdir()

        for studentcode in studentcodes:
            filepaths = get_path_file_of_student(studentcode)

            # Some users have handed in multiple files, be sure to copy them all
            iterations = 1
            if len(filepaths) > 1:
                iterations = len(filepaths)
            for i in range(iterations):
                folder_file_str = root_submission.name + '/' + filepaths[i].name
                shutil.copy(str(filepaths[i].resolve()), str(to_folder.resolve()))


def get_path_file_of_student(studentcode: str, folder: Path):
    # folder = Path(submissions_folder)
    if folder.exists():
        files = [child for child in folder.iterdir() if studentcode in child.name.lower()]
        # Rewriting this comprehension, to include handins without studentcode in name of file...
        if len(files) == 0: # Student have NOT included studentcode in filename...
            # Do a slow lookup in csv-file.
            # TODO: fix a quicker one...
            csvfile = get_csv_filename()
            with open(csvfile, 'r') as fh:
                content = csv.reader(fh)
                for line in content:
                    if studentcode in line[positions['usercode']]:
                        studentname = ''.join(line[positions['name']].lower().replace(',', '').split())
                        files = files = [child for child in folder.iterdir() if studentname in child.name.lower()]

        return files

def get_csv_filename(folder='zips'):
    '''
    Returns the filename of the csv-file stored in zips-folder
    '''
    csvs = [f for f in Path(folder).iterdir() if f.suffix == '.csv']
    if len(csvs) >= 1:
        return csvs[0]
    else:
        logging.error(f'CSV-file missing')
        raise FileNotFoundError('CSV-file does not exist in zips-folder')


def build_group_overview():
    for n in range(N_OF_GROUPS):
        groupset = find_group(n)
        if len(groupset) <= 0:
            continue
        if n in GROUPS:
            GROUPS[n] = GROUPS[n].update(groupset)
        else:
            GROUPS[n] = groupset

def find_group(group_number: int) -> set:
    group_name = f'Gruppe {group_number} '
    group_set = set()
    csvfile = get_csv_filename()
    with open(csvfile, 'r') as fh:
        content = csv.reader(fh)
        for i, line in enumerate(content):
            if group_name in line[positions['group_info']]:
                if 'Teststudent' == line[positions['name']]:
                    continue
                group_set.add(
                    line[positions['usercode']]
                )

    return group_set


def get_newest_file(zips):
    '''
    Find the most recent created file
    zips: Path
    returns a Path or None
    '''
    now = time()
    newest_file = None
    most_recent = now
    for f in zips.iterdir():
        if (this_filetime := (now - f.stat().st_mtime)) < most_recent:
            most_recent = this_filetime
            newest_file = f
    return newest_file.name

def already_unzipped(filename):
    with open(LOGFOLDER / LOGFILENAME) as logfile:
        for line in logfile.readlines()[::-1]:
            if filename in line:
                return True
        else:
            return False


if __name__ == '__main__':
    folder = Path('zips')
    filename = get_newest_file(folder)
    # Check if already unzipped this file
    if not already_unzipped(filename):
        unzip_file(str(folder / filename))
