from pathlib import Path
from time import time, ctime
from zipfile import ZipFile
import csv
import json
import logging
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from itertools import zip_longest


# csvfile = '2020-09-03T1057_Karakterer-INFO132.csv'
# Place the csvfile in the zips_folder

submissions_folder = 'submissions'

positions = {
    'name': 0,
    'usercode': 3,
    'group_info': 4,
}

with open('semester.json') as f:
    SETTINGS = json.load(f)

CONFIG = dict(
    COURSECODE = SETTINGS['COURSECODE'],
    N_OF_GROUPS = int(SETTINGS['N_OF_GROUPS'])
)

# Logging setup
LOGFOLDER = Path('logs')
LOGFILENAME = 'group_sorter.log'
logging.basicConfig(
                    filename=LOGFOLDER / LOGFILENAME,
                    format='%(levelname)s:%(asctime)s - %(message)s',
                    level=logging.DEBUG,
)
logging.info('Started')

@dataclass
class Groups:
    # Not typed == classvar
    all = dict()
    not_registered = set()

def get_submission_name(zipname: str) -> str:
    '''
    Extract the submission name from the name of the zipfile.
    Regular zipfile-name could be:
    '1599224423_837__INFO132-Temaoppgave_1_submissions.zip'
    [ctime] [coursecode] [submission_name]
    '''
    # If zipname is passed as a stringified path with folder, eg:
    # 'zips/1599224423_837__INFO132-Temaoppgave_1_submissions.zip',
    # this function strips the folders.
    # folder_pos = zipname.rfind('/')
    # zipname = zipname if folder_pos == -1 else zipname[folder_pos+1:]

    match = re.search('(' + CONFIG['COURSECODE'][:-3] + '[0-9]{3,4})-(.*[0-9])_(submissions)', zipname)
    if match:
        return match.group(2)
    else:
        # Did not find what we were after.
        return zipname.rstrip('.zip')

def get_zips() -> list:
    app_dir = Path('.')
    files = [str(f) for f in app_dir.glob('*.zip') if CONFIG['COURSECODE'] in f.name]
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

    if not Groups.all:
        build_group_overview()
    for n, studentcodes in Groups.all.items():
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
    Returns the Path of the csv-file stored in zips-folder
    '''
    csvs = [f for f in Path(folder).iterdir() if f.suffix == '.csv']
    if len(csvs) >= 1:
        return csvs[0]
    else:
        logging.error(f'CSV-file missing')
        raise FileNotFoundError('CSV-file does not exist in zips-folder')

def validate_group_vs_csv():
    csvfile = get_csv_filename()
    with open(csvfile, 'r') as fh:
        # lines = [l for l in csv.reader(fh)]
        csvdict = csv.DictReader(fh)
        all_students_codes = [codes['SIS Login ID'] for codes in csvdict]
        all_students_by_groups = {(n,code) for n,group in Groups.all.items()
                                  for code in group}

        # Difference from all codes vs them in groups;
        # Other words, find the student codes that are NOT in groups
        # diff = set(all_students_codes) - all_students_by_groups
        # print("Not in groups: ")
        # print(diff)

        with open('validation.csv', 'w') as validate:
            writer = csv.writer(validate)
            # [writer.writerow((l, g)) for l,g in zip_longest(all_students_codes, all_students_by_groups)]
        # print(Groups.all)
        # print(len(lines), len(groups))

        # assert len(Groups.all) == len(lines)


def build_group_overview():
    find_group()
    # for n in range(1, CONFIG['N_OF_GROUPS'] + 1):
    #     groupset = find_group(n)
    #     if len(groupset) <= 0:
    #         continue
    #     if n in Groups.all:
    #         # GROUPS[n] = GROUPS[n].update(groupset)
    #         Groups.all[n].update(groupset)
    #     else:
    #         Groups.all[n] = groupset
    # return Groups.all

def get_time_from_file(file, human=False):
    '''
    Return the ctime of the file
    or human readable if chosen
    '''
    # Check if filename contains ctime-info:
    # TODO
    ...


def find_group():
    csvfile = get_csv_filename()
    updated = csvfile.name[:15]
    print(f"Using csv-file from {updated}")
    logging.info(f"Using csv-file from {updated}")
    pattern = re.compile(fr"Gruppe [1-{CONFIG['N_OF_GROUPS']}]{{1,2}}")
    with open(csvfile, 'r') as fh:
        content = csv.DictReader(fh)
        for line in content:
            studentcode = line['SIS Login ID']
            hit = pattern.search(line['Section'])
            if hit:
                group_num = hit.group(0)[-2:].strip()
                Groups.all[group_num] = Groups.all.get(group_num, []) + [studentcode]
            # Student is not a member of group?
            else:
                Groups.not_registered.add(studentcode)
    logging.info(f"Studentcodes that are not sorted into groups: {Groups.not_registered}")


def get_newest_file(zips: str = 'zips'):
    '''
    Find the most recent created file
    zips: Path
    returns a Path or None
    Afterthought; The zipfile from canvas already includes ctime in the
    filename, making this function a bit over the board
    '''
    now = time()
    newest_file = None
    most_recent = now
    for f in Path(zips).iterdir():
        # If file is not a zip, skip
        if f.suffix != '.zip':
            continue
        if (this_filetime := (now - f.stat().st_mtime)) < most_recent:
            most_recent = this_filetime
            newest_file = f
    try:
        return newest_file.name
    except AttributeError:
        print(f'Could not find any recent files, please check {zips}-folder')

def already_unzipped(filename):
    if not Path(submissions_folder).exists():
        return False
    with open(LOGFOLDER / LOGFILENAME) as logfile:
        for line in logfile.readlines()[::-1]:
            if filename in line:
                return True
        else:
            return False


if __name__ == '__main__':
    folder = 'zips'
    filename = get_newest_file(folder)
    # Check if already unzipped this file
    if not already_unzipped(filename) and filename is not None:
        unzip_file(str(Path(folder) / filename))
    validate_group_vs_csv()
