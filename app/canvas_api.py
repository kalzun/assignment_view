import os
import requests as req
from requests_oauthlib import OAuth2Session, OAuth2
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
import json

# Store the account info in a file named:
env_name = '.env_secret'

env_path = Path('.') / env_name
load_dotenv(dotenv_path=env_path)

USERNAME = os.getenv('USERNAME')
TOKEN = os.getenv('TOKEN')
RESP_FILE = 'apiresponse.json'

course_id = '26755'
endpoint = f'https://mitt.uib.no/api/v1/courses/{course_id}/gradebook_history/feed'

def request_api():

    headers = {'Authorization': f'Bearer {TOKEN}'}
    # API returns a pagination, here we increase the results pr per_page
    # Must revisit this if we hit the API increasingly.
    payload = {'per_page': 200}
    resp = req.get(endpoint, headers=headers, params=payload)
    resp.raise_for_status()

    data = resp.json()
    save_data(data)
    return data


def get_data():
    # Check if apisresp.json is available, to spare calls to api
    try:
        with open(RESP_FILE) as fh:
            data = json.load(fh)
            print('Fetching data stored locally')
            return data
    except FileNotFoundError as e:
        print(f'{e} - {RESP_FILE} not found... Trying API!')
        return request_api()

def save_data(data):
    with open(RESP_FILE, 'w') as fh:
        json.dump(data, fh)
        print(f'Saved response from API to {RESP_FILE}')

if __name__ == '__main__':
    get_data()
