import asyncio
import logging
from instances import *
import time
from bot import send_balance
from nearApi import *


logging.basicConfig()
logger = logging.getLogger('balance')
logger.setLevel(logging.DEBUG)


def get_balance(username):
    logger.debug('Getting balance')
    resp = get_near_account_info(username).json()
    if 'error' in resp or 'result' not in resp:
        raise Exception(f'No result in balance request: {resp}')
    res = resp['result']
    logger.debug(f'Wallet status: {res}')
    balance = max(0, int(res['amount']) - res['storage_usage'] * 10 ** 19 - 5 * 10 ** 22)
    return balance


async def get_one_balance():
    while Q.empty() or Q.get_minimal_time() > time.time():
        await asyncio.sleep(0.2)
    tm, user_id, account, qid = Q.pop()
    balance = get_balance(account)
    old_balance = db.get_balance(user_id, account)
    db.update_balance(user_id, account, balance, int(time.time()))
    Q.add(user_id, account)
    if balance != old_balance:
        await send_balance(user_id, account, balance, old_balance)


async def run_balance():
    while True:
        await get_one_balance()
