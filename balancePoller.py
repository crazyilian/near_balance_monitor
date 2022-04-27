import asyncio
import logging
from instances import *
import time
from nearApi import *


logging.basicConfig()
logger = logging.getLogger('balance')
logger.setLevel(logging.DEBUG)

poller_tasks = dict()


def yocto(balance):
    return balance / 1e24


def formatN(balance):
    return f'Ⓝ {round(yocto(balance), 3)}'


def formatU(balance, usd):
    return f'${round(yocto(balance) * usd, 1)}'


async def send_balance(user_id, account, balance, old_balance):
    title = f'Balance at <code>{account}</code>'
    mul = db.get_account_mul(user_id, account)
    if old_balance is None:
        text = formatN(balance)
        if mul != 1.0:
            text += f' × {mul} = {formatN(balance * mul)}'
    else:
        old_balance_mul = old_balance * mul
        balance_mul = balance * mul
        delta_mul = balance_mul - old_balance_mul
        sign = '-' if delta_mul < 0 else '+'
        delta_mul = abs(delta_mul)
        text = f'{formatN(old_balance_mul)} {sign} {formatN(delta_mul)} = {formatN(balance_mul)}'
        if mul != 1.0:
            title += f' × {mul}'
    text = title + '\n' + text
    await bot.send_message(user_id, text, parse_mode='html')


async def get_balance(username):
    logger.debug(f'Getting balance of {username}')
    try:
        resp = await get_near_account_info(username)
        if 'error' in resp or 'result' not in resp:
            logger.exception(f'No result in balance request: {resp}')
            return None
    except Exception as e:
        logger.debug(f'Exception occurred while getting balance')
        logger.exception(e)
        return None
    res = resp['result']
    logger.debug(f'Wallet status: {res}')
    balance = max(0, int(res['amount']) - res['storage_usage'] * 10 ** 19 - 5 * 10 ** 22)
    logger.debug(f"Balance: {balance / 1e24}")
    return balance


def check_task_exists(user_id, account):
    return (user_id, account) in poller_tasks


async def remove_task(user_id, account):
    task = poller_tasks.pop((user_id, account))
    task.cancel()


async def run_task(user_id, account):
    was_error = False

    while True:
        upd_time = db.get_next_update_time(user_id, account)
        wait = max(0, upd_time - time.time())
        if was_error:
            was_error = False
            wait = min(wait, 60)
        await asyncio.sleep(wait)

        balance = await get_balance(account)
        db.update_timestamp(user_id, account, int(time.time()))
        if balance is None:
            was_error = True
        else:
            old_balance = db.get_balance(user_id, account)
            db.update_balance(user_id, account, balance)
            if balance != old_balance:
                await send_balance(user_id, account, balance, old_balance)


async def add_task(user_id, account):
    task = asyncio.create_task(run_task(user_id, account))
    poller_tasks[(user_id, account)] = task


async def recreate_tasks():
    for user_id, account in list(poller_tasks.keys()):
        await remove_task(user_id, account)
    for user_id in db.get_users():
        for account in db.get_accounts(user_id):
            await add_task(user_id, account)
