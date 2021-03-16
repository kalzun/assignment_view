from contextlib import closing
from dotenv import load_dotenv
from pathlib import Path
from typing import IO
import aiofiles
import aiohttp
import aiosqlite
import asyncio
import csv
import json
import logging
import os
import re
import requests as req
import sqlite3
import sys
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Store the account info in a file named:
env_name = ".env_secret"

env_path = Path(".") / env_name
load_dotenv(dotenv_path=env_path)

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
URLS = set()

stats = {
    "skipped": 0,
    "unique": set(),
    "last_update_time": 0,
}

# platform specific WINDOWS:
# https://github.com/encode/httpx/issues/914#issuecomment-622586610
if (
    sys.version_info[0] == 3
    and sys.version_info[1] >= 8
    and sys.platform.startswith("win")
):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def create_tables():
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
                modified_at REAL,
                display_name TEXT,
                code BLOB
            )"""
            )

            # Another table for meta-info about latest fetch, etc
            cursor.execute(
                """CREATE TABLE info
                (latest_fetch INTEGER)"""
            )
            cursor.execute("INSERT INTO info VALUES (?)", (0,))

            conn.commit()


def feedback_grade(params, endpoint, visible=False):
    resp = req.put(endpoint, params=params, headers=headers)
    return resp.status_code


def get_n_pages(resp):
    link = resp.headers.get("link", 0)
    if link:
        return int(re.search('(\d*).{15}rel="last"$', link).group(1))


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


async def fetch_endpoint(
    url: str, return_json: bool, session: aiohttp.ClientSession, **kwargs
) -> json:
    logger.debug(f"Fetching url {url}")
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    logger.debug(f"Fetched url {url}")
    if return_json:
        return await resp.json()
    return await resp.text()


async def get_specific_data(
    url: str, session: aiohttp.ClientSession, conn: aiosqlite.Connection, **kwargs
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
        logger.debug(f"Awaiting jsresp from {url}")
        js_resp = await fetch_endpoint(
            url=url, return_json=True, session=session, **kwargs
        )
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
        all_rows = []

        for data in js_resp:
            # We do not want to download a submissions that is
            # previously fetched:
            try:
                submitted_at = time.mktime(
                    time.strptime(data["submitted_at"], "%Y-%m-%dT%H:%M:%SZ")
                )
            except TypeError as er:
                logger.error(
                    f"Cannot parse submitted_at, probably because it is not submitted yet"
                )
                logger.error(f"submitted_at is: {data['submitted_at']}")
                submitted_at = 0
            if stats["last_update_time"] > submitted_at:
                logger.debug(f"Skipping {data['assignment_id']} - {data['user_id']}")
                stats["skipped"] += 1
                continue
            try:
                grader_id = data.get("grader_id", 0)
                # Grader_id is null from API, str(None) in python
                if grader_id == "None" or grader_id is None:
                    grader_id = 0
                grader_id = int(grader_id)
                assignment_id = int(data.get("assignment_id", 0))
                user_id = int(data.get("user_id", 0))
            except TypeError as er:
                logger.debug(
                    f"""{er} while converting
                                {data['grader_id']}
                                {type(data['grader_id'])}
                                {data['assignment_id']}
                                {type(data['assignment_id'])}
                                {data['user_id']}
                                {type(data['user_id'])}"""
                )
                grader_id = 0
                assignment_id = 0
                user_id = 0

            registered = USERS.get(user_id, None)
            if not registered:
                continue
            attachment_url = get_sublist(data.get("attachments", None)).get("url", None)
            try:
                logger.debug(
                    f"Awaiting response from code download from {attachment_url}"
                )
                text = await fetch_endpoint(
                    url=attachment_url, return_json=False, session=session, **kwargs
                )
                code = text
                code_modified = float(
                    time.mktime(
                        time.strptime(
                            get_sublist(data.get("attachments", None)).get(
                                "modified_at", None
                            ),
                            "%Y-%m-%dT%H:%M:%SZ",
                        )
                    )
                )
            except Exception as err:
                logger.error(f"Error during fetching code {err}")
                logger.debug(f"Error during fetching code {err}")
                code = "No submission found"
                code_modified = 0.0

            try:
                filename = str(
                    get_sublist(data.get("attachments", None)).get("filename", None)
                )
            except TypeError as err:
                logger.debug(
                    f"{err} while converting filename {get_sublist(data.get('attachments', None)).get('filename', None)}"
                )
                filename = "NO FILENAME"

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
                    filename,
                    code_modified,
                    str(
                        get_sublist(data.get("attachments", None)).get(
                            "display_name", None
                        )
                    ),
                    code,
                )
            )

        if all_rows:
            try:
                logger.debug(f"Awaiting DB executioins of all_rows")
                await conn.executemany(
                    """
                    INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    all_rows,
                )
                await conn.commit()
                logger.debug(f"Writing rows to db")
            except sqlite3.InterfaceError as err:
                logger.debug(f"Error {err} in this: {all_rows}")


async def fetch_all_paginated_pages(urls: list, **kwargs) -> None:
    """
    Consume the urls list, and write them to file
    """
    async with aiohttp.ClientSession(headers=headers) as session:
        async with aiosqlite.connect(DB, timeout=30) as conn:
            tasks = []
            for _ in range(len(URLS)):
                url = URLS.pop()
                tasks.append(
                    get_specific_data(url=url, session=session, conn=conn, **kwargs)
                )
            logger.debug(f"Awaiting tasks: {tasks}")
            await asyncio.gather(*tasks)


async def fetch_sections():
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await fetch_endpoint(
            sections_endpoint, return_json=True, session=session
        )

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


def clear_table():
    """
    Before making a solution to update values in db,
    we just clear the db when updating from API.
    """
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("DELETE FROM cache")
            cursor.execute("DELETE FROM info")
            cursor.execute("INSERT INTO info VALUES (?)", (0,))
            conn.commit()
            logger.debug("Cleared tables of records, stored stdvalue(0) in info-table")


def get_last_update_time():
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            stats["last_update_time"] = cursor.execute(
                "SELECT latest_fetch FROM info"
            ).fetchone()[0]
            conn.commit()
            logger.debug(f"Last update time: {stats['last_update_time']}.")


def set_last_update_time():
    with closing(sqlite3.connect(DB)) as conn:
        with closing(conn.cursor()) as cursor:
            logger.debug(f"Set last update time: {time.time()} <- (not prec).")
            cursor.execute("UPDATE info set latest_fetch=?", (time.time(),))
            conn.commit()


def db_validator():
    with closing(sqlite3.connect(DB)) as conn:
        try:
            cache, info = (
                conn.execute("SELECT * FROM cache").fetchone(),
                conn.execute("SELECT * FROM info").fetchone(),
            )
        except sqlite3.OperationalError as err:
            logger.debug(f"Db error, not setup tables - {err}")
            logger.debug(f"Creating tables")
            create_tables()
            return False

    return bool(cache)


def db_setup():
    if Path(DB).exists():
        logger.debug("Db is created")
        return True
    else:
        logger.debug("Db is not setup")
        create_tables()


async def main():
    global URLS

    db_validator()

    get_last_update_time()

    head = req.head(gradebook_endpoint, headers=headers)
    # Fx. if creds are not valid, it will fail here:
    # TODO feedback to UI
    head.raise_for_status()

    logger.debug(f"Headers from gradebook: {head.text}")

    # Make the urls list:
    pages = get_n_pages(head)
    logger.debug(f"N pages from gradebook: {pages}")
    URLS = set(make_urls(head, pages))

    # Fetch info about users
    logger.debug(f"Updating USERS")
    await update_users()
    logger.debug(f"Finished updating USERS")
    logger.debug(f"Starting fetching all submissions ")
    await fetch_all_paginated_pages(urls=URLS)
    logger.debug(f"Finished fetching all submissions ")

    set_last_update_time()
    get_last_update_time()


def build_assignments():
    asyncio.run(main())


def reset_db():
    """ Resets db """
    with closing(sqlite3.connect(DB)) as conn:
        conn.execute("DROP TABLE cache")
        conn.execute("DROP TABLE info")


if __name__ == "__main__":
    pass
    # build_assignments()
