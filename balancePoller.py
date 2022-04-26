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
    logger.debug(f'Getting balance of {username}')
    try:
        resp = get_near_account_info(username).json()
        if 'error' in resp or 'result' not in resp:
            logger.exception(f'No result in balance request: {resp}')
            return None
    except Exception as e:
        logger.exception(f'Exception occurred while getting balance')
        return None
    res = resp['result']
    logger.debug(f'Wallet status: {res}')
    balance = max(0, int(res['amount']) - res['storage_usage'] * 10 ** 19 - 5 * 10 ** 22)
    logger.debug(f"Balance: {balance / 1e24}")
    return balance


async def get_one_balance():
    while Q.empty() or Q.get_minimal_time() > time.time():
        await asyncio.sleep(0.2)
    tm, user_id, account = Q.pop()
    balance = get_balance(account)
    Q.add(user_id, account, 60)
    if balance is None:
        return
    old_balance = db.get_balance(user_id, account)
    db.update_balance(user_id, account, balance, int(time.time()))
    if balance != old_balance:
        await send_balance(user_id, account, balance, old_balance)


async def run_balance():
    while True:
        await get_one_balance()
