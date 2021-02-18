from pathlib import Path
from time import time, ctime
from zipfile import ZipFile
import csv
import json
import logging
import logging.config
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from itertools import zip_longest
from datetime import datetime


# csvfile = '2020-09-03T1057_Karakterer-INFO132.csv'
# Place the csvfile in the zips_folder

submissions_folder = "submissions"

positions = {
    "name": 0,
    "usercode": 3,
    "group_info": 4,
}

with open("semester.json") as f:
    SETTINGS = json.load(f)

CONFIG = dict(
    COURSECODE=SETTINGS["COURSECODE"], N_OF_GROUPS=int(SETTINGS["N_OF_GROUPS"])
)

# Logging setup
LOGFOLDER = Path("logs")
LOGFILENAME = "main.log"

logging.basicConfig(
                    filename=LOGFOLDER / LOGFILENAME,
                    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
                    level=logging.DEBUG,
)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
#Add RotateFileHandler to root logger
rfh = logging.handlers.RotatingFileHandler('logs/main.log', backupCount=2, maxBytes=1000000)
rfh.setFormatter(formatter)
logging.getLogger('').addHandler(rfh)

logger = logging.getLogger(__name__)

logger.info("Started")

LATEST_STATUS = Path("logs")


@dataclass
class Groups:
    # Not typed == classvar
    all = dict()
    not_registered = set()
    stats = {
        "submissions_total": 0,
        "submissions_pr_group": {},
    }


def get_submission_name(zipname: str) -> str:
    """
    Extract the submission name from the name of the zipfile.
    Regular zipfile-name could be:
    '1599224423_837__INFO132-Temaoppgave_1_submissions.zip'
    [ctime] [coursecode] [submission_name]
    """
    # If zipname is passed as a stringified path with folder, eg:
    # 'zips/1599224423_837__INFO132-Temaoppgave_1_submissions.zip',
    # this function strips the folders.
    # folder_pos = zipname.rfind('/')
    # zipname = zipname if folder_pos == -1 else zipname[folder_pos+1:]

    match = re.search(
        "(" + CONFIG["COURSECODE"][:-3] + "[0-9]{3,4})-(.*[0-9])_(submissions)", zipname
    )
    if match:
        return match.group(2)
    else:
        # Did not find what we were after.
        return zipname.rstrip(".zip")


def get_zips() -> list:
    app_dir = Path(".")
    files = [str(f) for f in app_dir.glob("*.zip") if CONFIG["COURSECODE"] in f.name]
    return files


def unzip_file(filepath) -> None:
    logger.info(f"Unzipping... ")
    if not filepath.exists():
        logger.warning(f"Filepath {filepath.name} does not exist... ")
        return False
    with ZipFile(filepath, "r") as zref:
        tmp_dir = tempfile.TemporaryDirectory()
        zref.extractall(tmp_dir.name)
        sort_to_group_folders(tmp_dir.name, filepath.name)
    logger.info(f"Successfully unzipped {filepath.name}")
    save_stats_of_groups()
    update_latest_file("zip", filepath.stat().st_mtime)


def sort_to_group_folders(tmpdir_name: str, zipname: str = "submissions"):
    # Ensure folder structure
    # submission > "Temaoppgave1" > gruppenummer
    submission_name = get_submission_name(zipname)
    root_submission = Path(submissions_folder)
    name_submission = root_submission / Path(submission_name)
    print(f"Extracting: {name_submission}")
    if not root_submission.exists():
        root_submission.mkdir()
    if not name_submission.exists():
        name_submission.mkdir()

    if not Groups.all:
        build_group_overview()

    Groups.stats["submissions_pr_group"][submission_name] = Groups.stats.get(
        submission_name, {}
    )

    for group_num, studentcodes in Groups.all.items():
        to_folder = root_submission / Path(submission_name) / Path(f"{group_num}")
        if not to_folder.exists():
            to_folder.mkdir()
        for studentcode in studentcodes:
            filepaths = get_path_file_of_student(studentcode, Path(tmpdir_name))
            # Some users have handed in multiple files, be sure to copy them all
            if len(filepaths) == 0:
                continue
                # iterations = len(filepaths)
            for i in range(len(filepaths)):
                folder_file_str = root_submission.name + "/" + filepaths[i].name
                shutil.copy(str(filepaths[i].resolve()), str(to_folder.resolve()))
            # For statistics:
            Groups.stats["submissions_total"] += 1
            Groups.stats["submissions_pr_group"][submission_name][group_num] = (
                Groups.stats["submissions_pr_group"][submission_name].get(group_num, 0)
                + 1
            )


def get_path_file_of_student(studentcode: str, folder: Path):
    # folder = Path(submissions_folder)
    pattern = re.compile(r"[-.,_ ]*")
    if folder.exists():
        files = [
            child for child in folder.iterdir() if studentcode in child.name.lower()
        ]
        # Rewriting this comprehension, to include handins without studentcode in name of file...
        if len(files) == 0:  # Student have NOT included studentcode in filename...
            # Do a slow lookup in csv-file.
            # TODO: fix a quicker one...
            csvfile = get_csv_filename()
            with open(csvfile, "r") as fh:
                content = csv.reader(fh)
                for line in content:
                    if studentcode in line[positions["usercode"]]:
                        studentname = re.sub(
                            pattern, "", line[positions["name"]].lower()
                        )
                        # studentname = ''.join(line[positions['name']].lower().replace(',', '').split())
                        files = [
                            child
                            for child in folder.iterdir()
                            if studentname in child.name.lower()
                        ]

        return files


def get_csv_filename(folder="zips"):
    """
    Returns the Path of the csv-file stored in zips-folder
    """
    csvs = [f for f in Path(folder).iterdir() if f.suffix == ".csv"]
    if len(csvs) >= 1:
        return csvs[0]
    else:
        logger.error(f"CSV-file missing")
        raise FileNotFoundError("CSV-file does not exist in zips-folder")


def validate_group_vs_csv():
    csvfile = get_csv_filename()
    with open(csvfile, "r") as fh:
        # lines = [l for l in csv.reader(fh)]
        csvdict = csv.DictReader(fh)
        all_students_codes = [codes["SIS Login ID"] for codes in csvdict]
        all_students_by_groups = {
            (n, code) for n, group in Groups.all.items() for code in group
        }

        # Difference from all codes vs them in groups;
        # Other words, find the student codes that are NOT in groups
        # diff = set(all_students_codes) - all_students_by_groups
        # print("Not in groups: ")
        # print(diff)

        with open("validation.csv", "w") as validate:
            writer = csv.writer(validate)
            # [writer.writerow((l, g)) for l,g in zip_longest(all_students_codes, all_students_by_groups)]
        # print(Groups.all)
        # print(len(lines), len(groups))

        # assert len(Groups.all) == len(lines)


def build_group_overview():
    csvfile, ctime_updated = get_newest_file(suffix=".csv")
    updated = csvfile.name[:15]

    print(f"Using csv-file from {updated} {datetime.utcfromtimestamp(ctime_updated)}")
    logger.info(f"Using csv-file from {updated}")

    pattern = re.compile(fr"Gruppe [1-{CONFIG['N_OF_GROUPS']}]{{1,2}}")
    with open(csvfile, "r") as fh:
        content = csv.DictReader(fh)
        for line in content:
            studentcode = line["SIS Login ID"]
            hit = pattern.search(line["Section"])
            if hit:
                group_num = hit.group(0)[-2:].strip()
                group = Groups.all.get(group_num, set())
                group.add(studentcode)
                Groups.all[group_num] = group
            # Student is not a member of group?
            else:
                Groups.not_registered.add(studentcode)
    logger.info(
        f"Studentcodes that are not sorted into groups: {Groups.not_registered}"
    )
    return Groups


def save_stats_of_groups():
    with open("semester.json") as read:
        sem = json.load(read)
        sem["stats"] = {
            "n_of_groups": len(Groups.all),
            "size_of_groups": [
                (g, len(students)) for g, students in Groups.all.items()
            ],
            "submissions_total": Groups.stats["submissions_total"],
            "submissions_pr_group": [
                (
                    submission_name,
                    [
                        (gr, n)
                        for groups in Groups.stats["submissions_pr_group"].values()
                        for gr, n in groups.items()
                    ],
                )
                for submission_name in Groups.stats["submissions_pr_group"]
            ],
        }
        with open("semester.json", "w") as out:
            json.dump(sem, out, indent=4)


def get_stats():
    with open("semester.json") as fh:
        sem = json.load(fh)
        return sem


def get_newest_file(folder: str = "zips", suffix: str = ".zip"):
    """
    Find the most recent created file
    folder: Path
    returns a Path or None
    Afterthought; The zipfile from canvas already includes ctime in the
    filename, making this function a bit over the board
    """
    now = time()
    newest_file = None
    most_recent = now
    for f in Path(folder).iterdir():
        # If file is not a chosen suffix
        if f.suffix != suffix:
            continue
        if (this_filetime := (now - f.stat().st_mtime)) < most_recent:
            most_recent = this_filetime
            newest_file = f
    try:
        return newest_file, newest_file.stat().st_mtime
    except AttributeError:
        print(f"Could not find any recent files, please check {folder}-folder")


def already_unzipped(filename):
    if not Path(submissions_folder).exists():
        return False
    with open(LOGFOLDER / LOGFILENAME) as logfile:
        for line in logfile.readlines()[::-1]:
            if filename.name in line:
                return True
        else:
            return False


def update_latest_file(which_file: str = "zip", updated: float = 0.0) -> None:
    with open("semester.json", "r") as read:
        sem = json.load(read)
        sem["last_updated"] = sem.get("last_updated", {})
        sem["last_updated"][which_file] = updated
        with open("semester.json", "w") as out:
            json.dump(sem, out, indent=4)


if __name__ == "__main__":
    folder = "zips"
    zippath, latest_zip = get_newest_file()
    csvpath, latest_csv = get_newest_file(suffix=".csv")

    with open("semester.json") as fh:
        sem = json.load(fh)
        zip_updated, csv_updated = (
            sem.get("last_updated", {}).get("zip", 0),
            sem.get("last_updated", {}).get("csv", 0),
        )

        if (
            latest_zip > zip_updated or latest_csv > csv_updated
        ) and zippath is not None:
            print(
                f"Using file '{zippath.name}' downloaded {datetime.utcfromtimestamp(latest_zip)}"
            )
            unzip_file(zippath)
        elif not already_unzipped(zippath) and zippath is not None:
            unzip_file(zippath)
