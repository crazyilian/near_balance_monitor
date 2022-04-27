import logging
import aiohttp


logging.basicConfig()
logger = logging.getLogger('near-api')
logger.setLevel(logging.DEBUG)

session = aiohttp.ClientSession()
REQUESTS_COUNTER = 0


async def get_near_account_info(username):
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
    resp = await (await session.post(url, json=data)).json()
    return resp


async def get_account_valid(username):
    logger.debug('Validating account')
    resp = await get_near_account_info(username)
    return 'error' not in resp


async def get_usd_currency():
    resp = await (await session.get('https://helper.mainnet.near.org/fiat')).json()
    return resp['near']['usd']
