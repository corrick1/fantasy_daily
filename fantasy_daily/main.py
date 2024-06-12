import requests
import json
from web3 import Web3
from datetime import datetime
from eth_account.messages import encode_defunct
import logging
from time import sleep
import random

#your path
keys_file_path = r'keys_and_addresses.txt'

web3 = Web3(Web3.HTTPProvider('https://rpc.envelop.is/blast'))

privy_app_id = 'clra3wyj700lslb0frokrj261'

def read_keys_and_addresses(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return [(index, line.strip().split(':')) for index, line in enumerate(lines, start=1) if line.strip()]

def login(private_key, wallet_address, account_number):
    try:
        init_payload = {'address': wallet_address}
        init_headers = {'Privy-App-Id': privy_app_id}
        init_response = requests.post('https://auth.privy.io/api/v1/siwe/init', json=init_payload, headers=init_headers)

        if init_response.status_code != 200:
            logging.error(f'Error during nonce request for account {account_number}: {wallet_address}')
            logging.error('Response: %s', init_response.text)
            return

        nonce_data = init_response.json()
        nonce = nonce_data['nonce']

        message = f"""www.fantasy.top wants you to sign in with your Ethereum account:
{wallet_address}

By signing, you are proving you own this wallet and logging in. This does not initiate a transaction or cost any fees.

URI: https://www.fantasy.top
Version: 1
Chain ID: 1
Nonce: {nonce}
Issued At: {datetime.utcnow().isoformat()}Z
Resources:
- https://privy.io"""

        signed_message = web3.eth.account.sign_message(encode_defunct(message.encode('utf-8')), private_key)

        auth_payload = {
            'chainId': 'eip155:1',
            'connectorType': 'injected',
            'message': message,
            'signature': signed_message.signature.hex(),
            'walletClientType': 'metamask'
        }

        auth_response = requests.post('https://auth.privy.io/api/v1/siwe/authenticate', json=auth_payload, headers=init_headers)

        if auth_response.status_code != 200:
            logging.error(f'Error during authentication for account {account_number}: {wallet_address}')
            logging.error('Response: %s', auth_response.text)
            return 

        auth_data = auth_response.json()

        logging.info(f'Authentication successful for account {account_number}: {wallet_address}')

        return auth_data
    except requests.exceptions.RequestException as e:
        logging.error(f'Error during authentication for account {account_number}: {wallet_address}', exc_info=True)

def privy_requests(data, address, account_number):
    try:
        headers = {
            'authority': 'www.fantasy.top',
            'method': 'POST',
            'path': '/api/auth/privy',
            'scheme': 'https',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Length': '1270',
            'Content-Type': 'application/json',
            'Cookie': f'privy-token={data["token"]}; privy-refresh-token={data["refresh_token"]}',
            'Origin': 'https://www.fantasy.top',
            'Priority': 'u=1, i',
            'Referer': 'https://www.fantasy.top/onboarding/home',
            'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }

        payload = {
            "user": {
                "id": data['user']['id'],
                "createdAt": data['user']['created_at'],
                "hasAcceptedTerms": True,
                "linkedAccounts": [
                    {
                        "address": address,
                        "chainId": "eip155:81457",
                        "chainType": "ethereum",
                        "connectorType": "injected",
                        "type": "wallet",
                        "verifiedAt": data["user"]["linked_accounts"][0]["verified_at"],
                        "walletClient": "unknown",
                        "walletClientType": "metamask"
                    },
                    {
                        "address": address,
                        "chainId": "eip155:1",
                        "chainType": "ethereum",
                        "connectorType": "embedded",
                        "recoveryMethod": "privy",
                        "type": "wallet",
                        "verifiedAt": data["user"]["linked_accounts"][1]["verified_at"],
                        "walletClient": "privy",
                        "walletClientType": "privy"
                    },
                    {
                        "name": data['user']['linked_accounts'][0]['name'],
                        "profilePictureUrl": data['user']['linked_accounts'][0]['profile_picture_url'],
                        "subject": data['user']['linked_accounts'][0]['subject'],
                        "type": "twitter_oauth",
                        "username": data['user']['linked_accounts'][0]['username'],
                        "verifiedAt": data["user"]["linked_accounts"][0]["verified_at"]
                    }
                ],
                "mfa_methods": [],
                "twitter": {
                    "name": data['user']['linked_accounts'][0]['name'],
                    "profilePictureUrl": data['user']['linked_accounts'][0]['profile_picture_url'],
                    "subject": data['user']['linked_accounts'][0]['subject'],
                    "username": data['user']['linked_accounts'][0]['username'],
                    "verifiedAt": data["user"]["linked_accounts"][0]["verified_at"]
                },
                "wallet": {
                    "address": address,
                    "chainId": "eip155:81457",
                    "chainType": "ethereum",
                    "connectorType": "injected"
                }
            }
        }

        response = requests.post('https://www.fantasy.top/api/auth/privy', json=payload, headers=headers)
        
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                return token
            else:
                logging.error(f'Token not found in response for account {account_number}: {address}')
                return None
        else:
            logging.error(f'Error during Privy request for account {account_number}: {address}', response.text)
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f'Error during Privy request for account {account_number}: {address}', exc_info=True)
        return None

def daily_claim(token, address, auth_data, account_number):
    try:
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Authorization': f'Bearer {token}',
            'Content-Length': '110',
            'Content-Type': 'application/json',
            'Cookie': f'privy-token={auth_data["token"]}; privy-session=t; privy-refresh-token={auth_data["refresh_token"]}; fan_cookie={token}',
            'Origin': 'https://www.fantasy.top',
            'Referer': 'https://www.fantasy.top/rewards',
            'Sec-Ch-Ua': '"Google Chrome";v="111", "Chromium";v="111", "Not=A?Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 uacq'
        }

        payload = {
            "queryName": "GET_PLAYER_DAILY_QUEST_HISTORY",
            "variables": {
                "id": address
            }
        }

        response = requests.post('https://www.fantasy.top/api/daily-quest', json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            record_day = data.get('data', {}).get('data', {}).get('update_daily_quest_history', {}).get('returning', [])[0].get('record_day')
            logging.info(f'Record day for account {account_number}: {record_day}')
            logging.info(json.dumps(data, indent=2))
        else:
            logging.error(f'Daily claim failed for account {account_number}: {address}!')
            logging.error(response.text)
    except requests.exceptions.RequestException as e:
        logging.error(f'Error during daily claim request for account {account_number}: {address}', exc_info=True)

def main():
    keys_and_addresses = read_keys_and_addresses(keys_file_path)

    for account_number, (private_key, address) in keys_and_addresses:
        if private_key and address:
            auth_data = login(private_key, address, account_number)
            if auth_data:
                token = privy_requests(auth_data, address, account_number)
                if token:
                    daily_claim(token, address, auth_data, account_number)
                    sleep(random.uniform(2, 5))  #random delay between 5 to 10 seconds

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    main()
