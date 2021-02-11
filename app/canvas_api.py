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


# Logging setup
LOGFOLDER = Path("logs")
LOGFILENAME = "group_sorter.log"
logging.basicConfig(
    filename=LOGFOLDER / LOGFILENAME,
    format="%(levelname)s:%(asctime)s - %(message)s",
    level=logging.DEBUG,
)
logging.info("Started")


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

USERS = {}


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


async def fetch_endpoint(url: str, session: aiohttp.ClientSession, **kwargs) -> json:
    # print(f"Fetching url {url}")
    resp = await session.request(method="GET", url=url, **kwargs)
    resp.raise_for_status()
    js_resp = await resp.json()
    return js_resp


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
        js_resp = await fetch_endpoint(url=url, session=session, **kwargs)
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as er:
        print(
            f'aiohttp exception for {url} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
        logging.error(
            f'aiohttp exception for {url} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
        return specific_data
    except Exception as e:
        print(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')

        logging.exception(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')
        return specific_data

    else:
        pattern = re.compile(",*\s")
        for data in js_resp:
            user_id = data["user_id"]
            registered = USERS.get(user_id, None)
            if not registered:
                continue
            specific_data = {
                "group": USERS[user_id].get("group", "NoGroup"),
                "sis_user_id": USERS[user_id]["sis_user_id"],
                "assignment_id": data["assignment_id"],
                "assignment_name": data["assignment_name"],
                "user_id": user_id,
                "user_name": pattern.sub("_", USERS[user_id]["name"]),
                "current_grade": data["current_grade"],
                "current_grader": data["current_grader"],
                "filename": get_sublist(data.get("attachments", None)).get(
                    "filename", None
                ),
                "display_name": get_sublist(data.get("attachments", None)).get(
                    "display_name", None
                ),
                "url": get_sublist(data.get("attachments", None)).get("url", None),
            }
            async with aiofiles.open(file, "a") as f:
                row = ",".join(str(value) for value in specific_data.values())
                await f.write(row + "\n")


async def write_one(file: IO, url: str, **kwargs) -> None:
    """
    Write the desired information from json to file.
    """
    resp = await get_specific_data(url=url, file=file, **kwargs)


async def fetch_all_paginated_pages(file: IO, urls: list, **kwargs) -> None:
    """
    Exhaust the urls list, and write them to file
    """
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for url in urls:
            tasks.append(write_one(file=file, url=url, session=session, **kwargs))
        await asyncio.gather(*tasks)


async def fetch_sections():
    # head = req.head(sections_endpoint, headers=headers)
    # pages = get_n_pages(head)
    # if pages > 1:
    #     # Endpoint as is today returns no pagination, with all users
    #     # as a list of dicts in sections.
    #     raise NotImplementedError('Sections API have changed, returns paginations\
    #                                 which is not implemented in your version.')
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await fetch_endpoint(sections_endpoint, session=session)

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
    if info["url"] is None:
        print(f"URL not found {info.items()}")
    filename = "_".join(value for value in list(info.values())[:-1]) + ".py"

    # This could be setup before ?
    assignment_path = Path(api_submission_folder) / Path(info["ass_name"])
    if not assignment_path.exists():
        assignment_path.mkdir()
    group_path = assignment_path.joinpath(Path(info["group"]))
    if not group_path.exists():
        group_path.mkdir()

    if Path(Path(group_path) / Path(filename)).exists():
        # print(f'{filename} already exists, skipping {info["url"]}')
        return

    # Download
    # print(f"Downloading url {info['url']}")
    try:
        resp = await session.request(method="GET", url=info["url"], **kwargs)
    except (
        aiohttp.ClientError,
        aiohttp.http_exceptions.HttpProcessingError,
    ) as er:
        print(
            f'aiohttp exception for {info["url"]} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
        logging.error(
            f'aiohttp exception for {info["url"]} {getattr(er, "status", None)}\
                                          {getattr(er, "message", None)}'
        )
    except Exception as e:
        print(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')

        logging.exception(f'Non-aiohttp exception occured {getattr(e, "__dict__", {})}')
    else:
        resp.raise_for_status()
        to_file = await resp.read()
        async with aiofiles.open(Path(group_path) / Path(filename), "wb") as f:
            await f.write(to_file)


async def fetch_submissions(fileinfo: list, **kwargs):
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = []
        for info in fileinfo:
            tasks.append(download_one(info=info, session=session, **kwargs))
        await asyncio.gather(*tasks)


def make_fileinfo_from_csv(file: IO) -> list:
    all_submissions = []
    with open(file) as f:
        for line in f.readlines():
            line = line.strip().split(",")
            fileinfo = {
                "group": line[0],
                "sis_id": line[1],
                "ass_id": line[2],
                "ass_name": line[3].replace(" ", "_"),
                "username": line[5],
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
        csvfile.rename("async_assignment.csv.bak")
    return csvfile


async def main():
    head = req.head(gradebook_endpoint, headers=headers)

    # Make the urls list:
    pages = get_n_pages(head)
    urls = make_urls(head, pages)

    csvfile = get_cache()
    if not Path(api_submission_folder).exists():
        Path(api_submission_folder).mkdir()

    await update_users()
    await fetch_all_paginated_pages(file=csvfile, urls=urls)
    all_submissions = make_fileinfo_from_csv(csvfile)
    await fetch_submissions(all_submissions)


def build_assignments():
    asyncio.run(main())



if __name__ == "__main__":
    build_assignments()
