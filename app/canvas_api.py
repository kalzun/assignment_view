import os
import requests as req
from requests_oauthlib import OAuth2Session, OAuth2
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
import json
import re
import csv

# Store the account info in a file named:
env_name = '.env_secret'

env_path = Path('.') / env_name
load_dotenv(dotenv_path=env_path)

USERNAME = os.getenv('USERNAME')
TOKEN = os.getenv('TOKEN')

RESP_FILE = 'apiresponse.json'
SUBMISSION_FOLDER = 'tmp_submission'

# Fields to use:
# assignment_id
# user_id (possible, but maybe use SIS instead)
# attachments:
#     - display_name
#     - filename
#     - url
# assignment_name
# user_name
# current_grade = complete | incomplete | null
# current_grader


course_id = '26755'
endpoint = f'https://mitt.uib.no/api/v1/courses/{course_id}/gradebook_history/feed'
headers = {'Authorization': f'Bearer {TOKEN}'}
payload = {'per_page': 50, 'page': 1}

def request_api():

    # API returns a pagination, here we increase the results pr per_page
    # Must revisit this if we hit the API increasingly.
    # Canvas is set to max 50 pr page.
    # To see how many pages that are still available after each page, 
    # see in header of the page under Link (relation is defined by RFC 5988)
    # eg:
    # <https://mitt.uib.no/api/v1/courses/26755/gradebook_history/feed?course_id=26755&format=json&page=1&per_page=50>; rel="current",
    # <https://mitt.uib.no/api/v1/courses/26755/gradebook_history/feed?course_id=26755&format=json&page=2&per_page=50>; rel="next",
    # <https://mitt.uib.no/api/v1/courses/26755/gradebook_history/feed?course_id=26755&format=json&page=1&per_page=50>; rel="first",
    # <https://mitt.uib.no/api/v1/courses/26755/gradebook_history/feed?course_id=26755&format=json&page=5&per_page=50>; rel="last"
    resp = req.get(endpoint, headers=headers, params=payload)
    resp.raise_for_status()

    save_data(resp.json(), 1)
    return resp

def make_csv(resp):
    dataset = resp.json()
    all_specific_data = []

    def get_sublist(sequence):
        attachments = []
        if sequence is None:
            return {}
        for elem in sequence:
            attachments.append(elem)
        if len(attachments) != 1:
            return {'filename': 'not found',
                    'display_name': 'not found',
                    'url': 'not found'
                    }
            # raise IndexError('Multiple attachments not handled!')
        return attachments[0]

    for data in dataset:
        specific_data = {
            'assignment_id': data['assignment_id'],
            'assignment_name': data['assignment_name'],
            'user_id': data['user_id'],
            'user_name': data['user_name'],
            'current_grade': data['current_grade'],
            'current_grader': data['current_grader'],
            'filename': get_sublist(data.get('attachments', None)).get('filename', None),
            'display_name': get_sublist(data.get('attachments', None)).get('display_name', None),
            'url': get_sublist(data.get('attachments', None)).get('url', None),
        }
        all_specific_data.append(specific_data)
        # save_specific_data(specific_data)


    # If respond header indicates that there are more pages, 
    # fetch all pages
    if (n_pages := get_n_pages(resp)) > 1:
        for n in range(2, n_pages + 1):
            payload['page'] = n
            nresponse = req.get(endpoint, headers=headers, params=payload)
            whole_data = nresponse.json()
            save_data(data, n)
            for data in whole_data:
                specific_data = {
                    'assignment_id': data['assignment_id'],
                    'assignment_name': data['assignment_name'],
                    'user_id': data['user_id'],
                    'user_name': data['user_name'],
                    'current_grade': data['current_grade'],
                    'current_grader': data['current_grader'],
                    'filename': get_sublist(data.get('attachments', None)).get('filename', None),
                    'display_name': get_sublist(data.get('attachments', None)).get('display_name', None),
                    'url': get_sublist(data.get('attachments', None)).get('url', None),
                }
                all_specific_data.append(specific_data)
                # save_specific_data(specific_data)
    save_specific_data(all_specific_data)


def download_submissions_with_api(data):
    '''
    Fetch the urls and download the submission
    Mark each submission with user_id
    Would use SIS Id, but is not provided in endpoint
    '''
    with open('resp.csv') as fh:
        csvfile = csv.DictReader(fh)
        for key, va in csvfile:
            print(key, va)


def save_specific_data(data):
    with open('resp.csv', 'a') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(data[0]))
        writer.writeheader()
        for elem in data:
            writer.writerow(elem)


def get_n_pages(resp):
    link = resp.headers.get('link', 0)
    if link:
        # Find last line
        lines = link.split(',')
        match = re.search('&page=[0-9]*', lines[-1])
        # Return the number of pages
        return int(match.group()[-2:].strip("="))


def get_data():
    # Check if apisresp.json is available, to spare calls to api
    user_inp = input("Fetch from API? (y/n): ")
    if user_inp.lower() == 'y':
        request_api()
        with open(RESP_FILE) as fh:
            return json.load(fh)
    else:
        try:
            with open(RESP_FILE) as fh:
                data = json.load(fh)
                print('Fetching data stored locally')
                return data
        except FileNotFoundError as e:
            print(f'{e} - {RESP_FILE} not found... Trying API!')
            request_api()
            with open(RESP_FILE) as fh:
                return json.load(fh)

def clear_csv():
    if Path('resp.csv').exists():
        Path('resp.csv').rename('old_resp.csv')

def save_data(data, page):
    with open(RESP_FILE, 'a') as fh:
        json.dump(data, fh)
        print(f'Saved response from API to {RESP_FILE}')

if __name__ == '__main__':
    # get_data()
    clear_csv()
    make_csv(request_api())
    download_submissions_with_api()
