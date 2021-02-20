from dotenv import load_dotenv
from pathlib import Path
from typing import IO
import aiofiles
import aiohttp
import asyncio
import csv
import json
import logging
import os
import re
import requests as req
import sys
import sqlite3
from contextlib import closing

# # Logging setup
# LOGFOLDER = Path("logs")
# LOGFILENAME = "group_sorter.log"
# logging.basicConfig(
#     filename=LOGFOLDER / LOGFILENAME,
#     format="%(levelname)s:%(asctime)s - %(message)s",
#     level=logging.DEBUG,
# )

logger = logging.getLogger(__name__)

# Store the account info in a file named:
env_name = ".env_secret"

env_path = Path(".") / env_name
load_dotenv(dotenv_path=env_path)

USERNAME = os.getenv("USERNAME")
TOKEN = os.getenv("TOKEN")

headers = {"Authorization": f"Bearer {TOKEN}"}
course_id = "26755"
gradebook_endpoint = (
    f"https://mitt.uib.no/api/v1/courses/{course_id}/gradebook_history/feed"
)
sections_endpoint = (
    f"https://mitt.uib.no/api/v1/courses/{course_id}/sections?include[]=students"
)
api_submission_folder = "api_submissions"

DB = "sqlite.db"
USERS = {}

stats = {
    "download_one": 0,
    "downloads": 0,
    "skipped": 0,
    "unique": set(),
}

# platform specific WINDOWS:
# https://github.com/encode/httpx/issues/914#issuecomment-622586610
if (
    sys.version_info[0] == 3
    and sys.version_info[1] >= 8
    and sys.platform.startswith("win")
):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def migrate():
    """
    Make table for db
    """
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:

            cursor.execute(
                """CREATE TABLE cache
                (group_nr INTEGER,
                sis_user_id TEXT,
                assignment_id INTEGER,
                assignment_name TEXT,
                user_id INTEGER,
                user_name TEXT,
                grader_id INTEGER,
                current_grade TEXT,
                current_grader TEXT,
                filename TEXT,
                display_name TEXT,
                code BLOB
            )"""
            )

            conn.commit()


def test_inserts():
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            resp = req.get('https://mitt.uib.no/files/3140327/download?download_frd=1&verifier=1Tvm0lGJPA3upziJK5kZpxsYIbXvKWkRH6brdm5i',
                                headers=headers)
            breakpoint()
            print(type(resp))
            logger.debug(resp)

            values = [
                (
                    1,
                    "mir101",
                    123,
                    "Temaoppgave_1",
                    4040,
                    "Landrok Kire",
                    431,
                    "complete",
                    "Saerdna Kire",
                    "1243_mir101.py",
                    "12341_mir101.py",
                    resp.text,
                )
            ]



            cursor.executemany(
                """
                INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                values,
            )

            rows = cursor.execute("SELECT * FROM cache").fetchall()
            print(rows)


def get_n_pages(resp):
    link = resp.headers.get("link", 0)
    if link:
        # Find last line
        lines = link.split(",")
        match = re.search("&page=[0-9]*", lines[-1])
        # Return the number of pages
        return int(match.group()[-2:].strip("="))


def make_urls(head: dict, max_n_pages: int) -> list:
    """
    Make a list of urls from the head of api
    Due to pagination of the API, it returns the last pagination in header['link']
    Returns a list of all the urls from the link-header
    So we can hit the api async
    """
    urls = []
    pattern = re.compile("https:\/\/[a-zA-Z.:&=0-9?_\/\/]*")

    for n in range(1, max_n_pages + 1):
        match = re.search(pattern, head.headers["link"])
        increase_pattern = re.compile("&page=[0-9]")
        if match:
            urls.append(increase_pattern.sub(f"&page={n}", match.group()))
    return urls


async def fetch_endpoint(url: str, return_json: bool, session: aiohttp.ClientSession, **kwargs) -> json:
    # print(f"Fetching url {url}")
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    if return_json:
        return await resp.json()
    return resp


async def get_specific_data(
    url: str, file: IO, session: aiohttp.ClientSession, **kwargs
) -> dict:
    specific_data = {}

    def get_sublist(sequence):
        attachments = []
        if sequence is None:
            return {}
        for elem in sequence:
            attachments.append(elem)
        if len(attachments) != 1:
            return {
                "filename": "not found",
                "display_name": "not found",
                "url": "not found",
            }
            # raise IndexError('Multiple attachments not handled!')
        return attachments[0]

    try:
        js_resp = await fetch_endpoint(url=url, return_json=True, session=session, **kwargs)
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as er:
        logger.error(
            f'aiohttp exception for {url} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
        return specific_data
    except Exception as e:
        logger.exception(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')
        return specific_data

    else:
        pattern = re.compile(",*\s")
        with closing(sqlite3.connect(DB)) as conn:
            with closing(conn.cursor()) as cursor:
                conn.commit()
                all_rows = []

                for data in js_resp:
                    try:
                        grader_id = data.get("grader_id", 0)
                        # Grader_id is null from API, str(None) in python
                        if grader_id == 'None' or grader_id is None:
                            grader_id = 0
                        grader_id = int(grader_id)
                        assignment_id = int(data.get("assignment_id", 0))
                        user_id = int(data.get("user_id", 0))
                    except TypeError as er:
                        logger.debug(f"""{er} while converting
                                        {data['grader_id']}
                                        {type(data['grader_id'])}
                                        {data['assignment_id']}
                                        {type(data['assignment_id'])}
                                        {data['user_id']}
                                        {type(data['user_id'])}""")
                        grader_id = 0
                        assignment_id = 0
                        user_id = 0

                    registered = USERS.get(user_id, None)
                    if not registered:
                        continue
                    attachment_url = get_sublist(data.get("attachments", None)).get("url", None)
                    try:
                        resp = await fetch_endpoint(
                            url=attachment_url, return_json=False, session=session, **kwargs)
                        code = await resp.text()
                    except:
                        code = 'No submission found'
                    all_rows.append(
                        (
                            int(USERS[user_id].get("group", "NoGroup")),
                            str(USERS[user_id]["sis_user_id"]),
                            assignment_id,
                            str(data["assignment_name"]),
                            user_id,
                            str(pattern.sub("_", USERS[user_id]["name"])),
                            grader_id,
                            str(data["current_grade"]),
                            str(data["current_grader"]),
                            str(get_sublist(data.get("attachments", None)).get(
                                "filename", None
                            )),
                            str(get_sublist(data.get("attachments", None)).get(
                                "display_name", None
                            )),
                            code,
                        )
                    )
                try:
                    cursor.executemany(
                        """
                        INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        all_rows,
                    )
                    conn.commit()
                except sqlite3.InterfaceError as er:
                    logger.debug(all_rows)
                    logger.debug(f"Trying to insert but failing - {er}")

            # async with aiofiles.open(file, "a", encoding="utf-8", newline="") as f:
            #     row = ",".join(str(value) for value in specific_data.values())
            #     await f.write("\n" + row)


async def write_one(file: IO, url: str, **kwargs) -> None:
    """
    Write the desired information from json to file.
    """
    resp = await get_specific_data(url=url, file=file, **kwargs)


async def fetch_all_paginated_pages(file: IO, urls: list, **kwargs) -> None:
    """
    Consume the urls list, and write them to file
    """
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for url in urls:
            tasks.append(write_one(file=file, url=url, session=session, **kwargs))
        await asyncio.gather(*tasks)


async def fetch_sections():
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await fetch_endpoint(sections_endpoint, return_json=True, session=session)

    users = {}
    # Make a dict of users so we can lookup when making lookups for users
    for group in resp:
        group_nr = group.get("sis_section_id", None)
        # Groupnr/ is a section_id in this format:
        # YEARV-COURSECODE-N-N-N
        # Where the last integer reflects the visible group number
        # Hence the slice in assignment below
        if not group_nr:
            # skip groups that are not member of sections
            continue
        if "students" not in group:  # This may be unnecessary
            continue
        for user in group["students"]:
            user_id = user.get("id", None)
            users[user_id] = {
                "sis_user_id": user.get("sis_user_id", None),
                "name": user.get("sortable_name", None),
                "group": group_nr[-1],
            }
    return users


async def update_users():
    global USERS
    # Yeah, uses global here
    USERS = await fetch_sections()


async def download_one(info: dict, session: aiohttp.ClientSession, **kwargs) -> None:
    stats["download_one"] += 1

    url = info["url"]
    if url is None:
        print(f"URL not found {info.items()}")
        return
    if info["grader_id"] != "None":
        # Skip downloading the submissions that are graded
        stats["skipped"] += 1
        logger.debug(f"Skipping downloading {info.items()}.")
        return

    if url in stats["unique"]:
        stats["skipped"] += 1
        logger.debug(f"Already in unique set {info.items()} -  {url}.\n")
        return

    stats["unique"].add(url)

    filename = "_".join(value for value in list(info.values())[:-1]) + ".py"

    # TODO This making of dirs could be setup before !
    assignment_path = Path(api_submission_folder) / Path(info["ass_name"])

    if not assignment_path.exists():
        assignment_path.mkdir()
    group_path = assignment_path.joinpath(Path(info["group"]))
    if not group_path.exists():
        group_path.mkdir()

    if Path(Path(group_path) / Path(filename)).exists():
        logger.debug(f'{filename} already exists, skipping {info["url"]}')
        stats["skipped"] += 1
        return

    # Download
    try:
        resp = await session.request(method="GET", url=info["url"], **kwargs)
        resp.raise_for_status()
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as er:
        logger.error(
            f'aiohttp exception for {info["url"]} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
    except Exception as e:
        logger.exception(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')
    else:
        to_file = await resp.read()
        async with aiofiles.open(Path(group_path) / Path(filename), "wb") as f:
            await f.write(to_file)
            stats["downloads"] += 1


async def fetch_submissions(fileinfo: list, **kwargs):
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for info in fileinfo:
            tasks.append(download_one(info=info, session=session, **kwargs))
        await asyncio.gather(*tasks)


def make_fileinfo_from_csv(file: IO) -> list:
    all_submissions = []
    with open(file, encoding="utf-8", newline="") as f:
        for line in f.readlines():
            line = line.strip().split(",")
            # TODO
            # Make a sweeter check and lookup here
            if len(line) < 6:
                continue
            fileinfo = {
                "group": line[0],
                "sis_id": line[1],
                "ass_id": line[2],
                "ass_name": line[3].replace(" ", "_"),
                "username": line[5],
                "grader_id": line[6],
                "current_grade": line[7],
                "url": line[-1],
            }
            if fileinfo["url"] is None:
                # No submission
                continue
            all_submissions.append(fileinfo)
    all_submissions = sorted(all_submissions, key=lambda elem: elem["group"])
    return all_submissions


def get_cache():
    csvfile = Path("async_assignment.csv")
    if csvfile.exists():
        csvfile.replace("async_assignment.csv.bak")
    return csvfile


async def main():
    head = req.head(gradebook_endpoint, headers=headers)

    # Make the urls list:
    pages = get_n_pages(head)
    urls = make_urls(head, pages)

    csvfile = get_cache()
    if not Path(api_submission_folder).exists():
        Path(api_submission_folder).mkdir()

    # Fetch info about users
    await update_users()
    # Get info about submisisons, users and their submission urls
    # "Cache" this to csv
    await fetch_all_paginated_pages(file=csvfile, urls=urls)
    # all_submissions = make_fileinfo_from_csv(csvfile)
    # await fetch_submissions(all_submissions)

    print("\nStats: ")
    print(f"Users: {len(USERS)}")
    for k, v in stats.items():
        if k == "unique":
            continue
        print(f"{k}: {v}")


def build_assignments():
    asyncio.run(main())


if __name__ == "__main__":
    pass
    # build_assignments()

