import logging
import requests


logging.basicConfig()
logger = logging.getLogger('near-api')
logger.setLevel(logging.DEBUG)

REQUESTS_COUNTER = 0


def get_near_account_info(username):
    global REQUESTS_COUNTER
    REQUESTS_COUNTER += 1
    logger.debug('Calling near api...')
    url = 'https://rpc.mainnet.near.org'
    data = {
        "method": "query",
        "params": {
            "request_type": "view_account",
            "account_id": username,
            "finality": "optimistic"
        },
        "id": 1,
        "jsonrpc": "2.0"
    }
    resp = requests.post(url, json=data)
    return resp


def get_account_valid(username):
    logger.debug('Validating account')
    resp = get_near_account_info(username).json()
    return 'error' not in resp


def get_usd_currency():
    return requests.get('https://helper.mainnet.near.org/fiat').json()['near']['usd']
