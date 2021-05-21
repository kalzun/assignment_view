import asyncio
import csv
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from io import BytesIO
from pathlib import Path
from typing import IO
from zipfile import ZipFile

import aiofiles
import aiohttp
import aiosqlite
import requests as req
from aiohttp import ClientResponseError
from dotenv import load_dotenv
from flask import current_app

from .db import get_db
from .db import get_db_path

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

    with closing(get_db()) as conn:
        # Another table for meta-info about latest fetch, etc
        conn.execute(
            """CREATE TABLE info
            (latest_fetch INTEGER)"""
        )

        # Another table for submissions -
        conn.execute(
            """CREATE TABLE submissions
            (submission_id INTEGER,
            assignment_id INTEGER,
            assignment_name TEXT,
            grader_id INTEGER,
            current_grade TEXT,
            current_grader TEXT,
            group_nr INTEGER,
            sis_user_id TEXT,
            user_name TEXT,
            user_id INTEGER
            )"""
        )

        # Another table for attachments - for multiple attachments
        conn.execute(
            """CREATE TABLE attachments
            (displayname TEXT,
            filename TEXT,
            modified_at REAL,
            code BLOB,
            submission_id INTEGER,
            FOREIGN KEY(submission_id) REFERENCES submissions(submission_id)
            )"""
        )

        conn.execute("INSERT INTO info VALUES (?)", (0,))

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


def fetch_endpoint_blocking(url: str, params, _headers=None) -> json:
    if _headers is None:
        _headers = headers
    logger.debug(f"Fetching url {url}")
    resp = req.get(url=url, params=params, headers=headers)
    resp.raise_for_status()
    logger.debug(f"Fetched url {url}")
    return resp.json()


async def fetch_endpoint(
    url: str, return_json: bool, session: aiohttp.ClientSession, **kwargs
) -> json:

    if url == "not found":
        return url

    logger.debug(f"Fetching url {url}")
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    logger.debug(f"Fetched url {url}")
    if return_json:
        return await resp.json()
    return resp


async def unzip_file(
    url: str,
    submission_id: int,
    session=aiohttp.ClientSession,
    conn=aiosqlite.Connection,
    **kwargs,
) -> None:
    """Download a zip-file, decompress in tmp-folder, read to db"""
    async with aiohttp.ClientSession() as session:
        resp = await fetch_endpoint(url, return_json=False, session=session, **kwargs)
        filebyte = await resp.read()
        with ZipFile(BytesIO(filebyte)) as zref:
            tmp_dir = tempfile.TemporaryDirectory()
            zref.extractall(tmp_dir.name)
            for file in Path(tmp_dir.name).iterdir():
                # Skip directories
                if file.is_dir():
                    continue
                async with aiofiles.open(file) as f:
                    content = await f.read()
                    await conn.execute(
                        """INSERT INTO attachments VALUES
                        (?,
                        ?,
                        ?,
                        ?,
                        ?)""",
                        (
                            file.name,
                            file.name,
                            file.stat().st_ctime,
                            content,
                            submission_id,
                        ),
                    )
            logger.info(f"Successfully unzipped {tmp_dir.name}")


async def cache_attachments(
    attachments: list,
    submission_id: int,
    session: aiohttp.ClientSession,
    conn: aiosqlite.Connection,
    **kwargs,
) -> None:
    # Loop through list of attachments, storing each attachment in db by submission_id as FK.

    logger.debug(f"Inside cache_attachments - {submission_id=} - {attachments=} ")

    if attachments is None:
        logger.debug(f"{submission_id} has no attachments")
        return

    for att in attachments:
        url = att.get("url", None)

        # Skip if no url to file-attachment
        if url is None:
            continue

        if att["size"] == "null" or att["size"] == None:
            logger.debug(
                f"Something wrong during upload, {att['filename']=} not valid. ({att['size']=})"
            )
            continue

        resp = await fetch_endpoint(url, return_json=False, session=session, **kwargs)

        logger.debug(f"{'zip' in att['content-type']} - {att['content-type']}")
        if "zip" in att["content-type"]:
            # TODO: Unzip
            await unzip_file(url, submission_id, session, conn)
            logger.debug(f"Should unzip {url}")

        else:
            code = await resp.text()
            # Write to db using user_id as FK
            await conn.execute(
                """INSERT INTO attachments VALUES
                (?,
                ?,
                ?,
                ?,
                ?)""",
                (
                    att.get("display_name", None),
                    att.get("filename", None),
                    att.get("modified_at", None),
                    code,
                    submission_id,
                ),
            )
            await conn.commit()


async def cache_submissions(
    url: str,
    session: aiohttp.ClientSession,
    conn: aiosqlite.Connection,
    **kwargs,
) -> None:
    # Store every submission to cache db - and each attachment will be
    # solved in other function (and table)

    specific_data = {}
    # For name replacer "LastName, FirstName" -> "LastName_FirstName"
    name_pattern = re.compile(",*\s")

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
                logger.debug(
                    f"Last update ({time.ctime(stats['last_update_time'])})\
                      more recent than submission ({time.ctime(submitted_at)}) \
                      Skipping {data['assignment_id']=} - {data['user_id']=}"
                )
                stats["skipped"] += 1
                continue

            grader_id = data.get("grader_id", 0)
            # Grader_id is null from API, str(None) in python
            if grader_id == "None" or grader_id is None:
                grader_id = 0
            try:
                grader_id = int(grader_id)
                assignment_id = int(data.get("assignment_id", 0))
                user_id = int(data.get("user_id", 0))
            except TypeError as er:
                grader_id = 0
                assignment_id = 0
                user_id = 0
                logger.debug(
                    f"""{er} while converting
                                {data['grader_id']}
                                {type(data['grader_id'])}
                                {data['assignment_id']}
                                {type(data['assignment_id'])}
                                {data['user_id']}
                                {type(data['user_id'])}"""
                )

            registered_user = USERS.get(user_id, None)
            if not registered_user:
                logger.debug(f"{user_id} not registered, not fetching submission")
                continue
            submission_id = int(data["id"])

            # Fetch attachments
            attachments = data.get("attachments", None)

            await cache_attachments(
                attachments, submission_id, session=session, conn=conn
            )

            if attachments is None:
                logger.debug(
                    f"No attachment discovered on {user_id=} {assignment_id=} - probably no submission"
                )

            subm = (
                submission_id,
                assignment_id,
                str(data["assignment_name"]),
                grader_id,
                data["current_grade"],
                data["current_grader"],
                int(USERS[user_id].get("group", "NoGroup")),
                str(USERS[user_id]["sis_user_id"]),
                str(name_pattern.sub("_", USERS[user_id]["name"])),
                user_id,
            )

            logger.debug(f"Inserting into db: {subm}")

            await conn.execute(
                """INSERT INTO submissions VALUES (?,?,?,?,?,?,?,?,?,?)""",
                subm,
            )
            await conn.commit()
            logger.debug(f"To db: {subm}")
    logger.debug(f"Skipped {stats['skipped']}")


async def fetch_all_paginated_pages(urls: list, **kwargs) -> None:
    """
    Consume the urls list, fetch all submissions, store in sql
    """
    async with aiohttp.ClientSession(headers=headers) as session:
        async with aiosqlite.connect(get_db_path(), timeout=30) as conn:
            tasks = []
            for _ in range(len(URLS)):
                url = URLS.pop()
                tasks.append(
                    cache_submissions(url=url, session=session, conn=conn, **kwargs)
                )
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
        group_nr = group_nr.split("-")[-1]
        if "students" not in group:  # This may be unnecessary
            continue
        for user in group["students"]:
            user_id = user.get("id", None)
            users[user_id] = {
                "sis_user_id": user.get("sis_user_id", None),
                "name": user.get("sortable_name", None),
                "group": group_nr,
            }
    return users


async def update_users():
    global USERS
    # Yeah, uses global here
    USERS = await fetch_sections()
    with open("users.json", "w") as f:
        json.dump(USERS, f)


def clear_table():
    """
    Before making a solution to update values in db,
    we just clear the db when updating from API.
    """
    conn = get_db()
    conn.execute("DELETE FROM info")
    conn.execute("INSERT INTO info VALUES (?)", (0,))
    conn.commit()
    logger.debug("Cleared tables of records, stored stdvalue(0) in info-table")


def get_last_update_time():
    conn = get_db()
    stats["last_update_time"] = conn.execute(
        "SELECT latest_fetch FROM info"
    ).fetchone()[0]
    conn.commit()
    logger.debug(f"Last update time: {stats['last_update_time']}.")


def set_last_update_time():
    conn = get_db()
    logger.debug(f"Set last update time: {time.time()} <- (not prec).")
    conn.execute("UPDATE info set latest_fetch=?", (time.time(),))
    conn.commit()


def db_validator():
    conn = get_db()
    try:
        info, submissions, attachments = (
            conn.execute("SELECT * FROM info").fetchone(),
            conn.execute("SELECT * FROM submissions").fetchone(),
            conn.execute("SELECT * FROM attachments").fetchone(),
        )
    except sqlite3.OperationalError as err:
        logger.debug(f"Db error, not setup tables - {err}")
        logger.debug(f"Creating tables")
        create_tables()
        return False

    return bool(submissions)


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

    # DEBUG reduce pageload:
    # pages = 25
    # logger.debug(f"DEBUGGIN _ REDUCING PAGELOAD! PAGES LOADED {pages}!")

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


if __name__ == "__main__":
    pass
    # build_assignments()
