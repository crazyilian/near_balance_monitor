import re
from instances import *
import logging
import nearApi


logging.basicConfig()
logger = logging.getLogger('TeleBot')
logger.setLevel(logging.DEBUG)


def yocto(balance):
    return balance / 1e24


def formatN(balance):
    return f'Ⓝ {round(yocto(balance), 3)}'


def formatU(balance, usd):
    return f'${round(yocto(balance) * usd, 1)}'


async def send_balance(user_id, account, balance, old_balance):
    mul = db.get_account_mul(user_id, account)
    if old_balance is None:
        text = formatN(balance)
        if mul != 1.0:
            text += f' × {mul} = {formatN(balance * mul)}'
    else:
        delta = balance - old_balance
        sign = '-' if delta < 0 else '+'
        delta = abs(delta)
        text = f'{formatN(old_balance)} {sign} {formatN(delta)} = {formatN(balance)}'
        if mul != 1.0:
            old_balance_mul = old_balance * mul
            balance_mul = balance * mul
            delta_mul = balance - old_balance
            sign = '-' if delta_mul < 0 else '+'
            delta_mul = abs(delta_mul)
            text += f'\n× {mul}\n'
            text += f'{formatN(old_balance_mul)} {sign} {formatN(delta_mul)} = {formatN(balance_mul)}'

    title = f'Balance at <code>{account}</code>'
    text = title + '\n' + text
    await bot.send_message(user_id, text, parse_mode='html')


def parse_unique_arguments(command):
    return list(dict.fromkeys(filter(lambda x: len(x) > 0, re.split(" |,|;|\n|\t", command)[1:])))


@botdp.message_handler(lambda msg: not db.check_user_registered(msg.from_user.id), content_types=['text'])
async def handle_new_user(message):
    user = message.from_user
    db.register_user(user.id, user.username)
    print(f'New user: {user.username}')
    await help_message(message)


@botdp.message_handler(commands=['help', 'start'])
async def help_message(message):
    user = message.from_user
    tm = db.get_update_interval(user.id)
    updates_interval = str(5 if tm is None else tm // 60 if tm % 60 == 0 else round(tm / 60, 2))
    mins = 'minutes' if updates_interval != '1' else 'minute'
    msg = '''
Bot that tracks your [Near wallet](https://wallet.near.org) balances. If the balance has changed, the bot \
will send you a message. Check for updates every ''' + updates_interval + ' ' + mins + '''. \
To change this time please contact the developer.

⸻ _Main commands_ ⸻

`{accs}` is a list of accounts separated by space, comma, etc.
Leave empty to pass all accounts you have (except for `/add` and `/remove` commands).

`/add {accs}` — add new tracking accounts.
`/remove {accs}` — remove accounts from tracking.
`/balance {accs}` — get balance of given accounts.

⸻ _Multiplier_ ⸻

Multiplier shows your balance multiplied by the given coefficient.
`{x}` equals to 1.0 means 100% of your balance. `{x}` is float, 0 ≤ `{x}`.

`/get_multiplier {accs}` — get accounts multiplier.
`/set_multiplier {x} {accs}` — set accounts multiplier.

⸻ _Other_ ⸻

`/help` — this message.
    '''
    await bot.send_message(user.id, msg, parse_mode='Markdown', disable_web_page_preview=True)


@botdp.message_handler(commands=['add'])
async def command_add(message):
    user = message.from_user
    accounts = parse_unique_arguments(message.text)
    if len(accounts) == 0:
        await bot.send_message(user.id, "No accounts specified")
        return
    msgs = []
    for acc in accounts:
        if not db.check_account_validated(user.id, acc) and not nearApi.get_account_valid(acc):
            msgs.append(f"<code>{acc}</code> not valid")
        elif db.add_account(user.id, acc):
            msgs.append(f"<code>{acc}</code> added")
            Q.add(user.id, acc)
        else:
            msgs.append(f"<code>{acc}</code> already exists")
    msg = '\n'.join(msgs)
    await bot.send_message(user.id, msg, parse_mode='html')


@botdp.message_handler(commands=['remove'])
async def command_remove(message):
    user = message.from_user
    accounts = parse_unique_arguments(message.text)
    if len(accounts) == 0:
        await bot.send_message(user.id, "No accounts specified")
        return
    msgs = []
    for acc in accounts:
        if db.remove_account(user.id, acc):
            msgs.append(f"<code>{acc}</code> removed")
            Q.remove(user.id, acc)
        else:
            msgs.append(f"<code>{acc}</code> doesn't exist")
    msg = '\n'.join(msgs)
    await bot.send_message(user.id, msg, parse_mode='html')


@botdp.message_handler(commands=['balance', 'balance_usd'])
async def command_total(message):
    user = message.from_user
    accounts = parse_unique_arguments(message.text)
    if len(accounts) == 0:
        accounts = db.get_accounts(user.id)
    msgs = []
    if message.text.split()[0] == '/balance':
        formatF = formatN
    else:
        usd = nearApi.get_usd_currency()
        msgs.append(f'Ⓝ 1 ≈ ${usd}')
        formatF = lambda x: formatU(x, usd)
    total = 0
    total_mul = 0
    valid_accounts_cnt = 0
    for acc in accounts:
        balance = db.get_balance(user.id, acc)
        if balance is None:
            msgs.append(f"<code>{acc}</code> doesn't exist")
        else:
            valid_accounts_cnt += 1
            mul = db.get_account_mul(user.id, acc)
            balance_mul = balance * mul
            total += balance
            total_mul += balance_mul
            msgs.append(f"<code>{acc}</code>\n{formatF(balance)} × {mul} = {formatF(balance_mul)}")
    if valid_accounts_cnt > 1:
        msgs.append(f'<i>Total:</i>\n{formatF(total)} × α = {formatF(total_mul)}')
    msg = '\n\n'.join(msgs)
    await bot.send_message(user.id, msg, parse_mode='html')


def parse_positive_float(s):
    if s.isdigit():
        return float(s)
    a = s.split('.')
    if len(a) != 2 or not a[0].isdigit() or not a[1].isdigit():
        return None
    x = round(float(s), 2)
    return x


@botdp.message_handler(commands=['set_multiplier'])
async def command_set_multiplier(message):
    user = message.from_user
    args = parse_unique_arguments(message.text)
    if len(args) == 0:
        await bot.send_message(user.id, 'Multiplier is not specified')
        return
    num, *accounts = args
    mul = parse_positive_float(num)
    if mul is None:
        await bot.send_message(user.id, f'<code>{num}</code> is not a valid float', parse_mode='html')
        return
    if len(accounts) == 0:
        accounts = db.get_accounts(user.id)
    msgs = []
    for acc in accounts:
        if not db.set_account_mul(user.id, acc, mul):
            msgs.append(f"<code>{acc}</code> doesn't exists")
        else:
            msgs.append(f"<code>{acc}</code> multiplier set to {mul}")
    msg = '\n'.join(msgs)
    await bot.send_message(user.id, msg, parse_mode='html')


@botdp.message_handler(commands=['get_multiplier'])
async def command_get_multiplier(message):
    user = message.from_user
    accounts = parse_unique_arguments(message.text)
    if len(accounts) == 0:
        accounts = db.get_accounts(user.id)
    msgs = []
    for acc in accounts:
        mul = db.get_account_mul(user.id, acc)
        if mul is None:
            msgs.append(f"<code>{acc}</code> doesn't exists")
        else:
            msgs.append(f"<code>{acc}</code>  × {mul}")
    msg = '\n'.join(msgs)
    await bot.send_message(user.id, msg, parse_mode='html')


@botdp.message_handler(lambda msg: msg.from_user.id == 404377069, commands=['set_update_interval'])
async def command_set_update_interval(message):
    user = message.from_user
    client_id, seconds = parse_unique_arguments(message.text)
    try:
        client_id = int(client_id)
    except Exception as e:
        await bot.send_message(user.id, f'<code>{client_id}</code> is incorrect id', parse_mode='html')
        return
    if not seconds.isdigit():
        await bot.send_message(user.id, f'<code>{seconds}</code> is incorrect num', parse_mode='html')
        return
    else:
        seconds = int(seconds)
    db.set_update_interval(client_id, seconds)
    await bot.send_message(user.id, f'<code>{client_id}</code> update interval set to {seconds} seconds', parse_mode='html')
    await bot.send_message(client_id, f'Your balance update interval is {seconds} seconds now.')


@botdp.message_handler(lambda msg: msg.from_user.id == 404377069, commands=['get_update_interval'])
async def command_get_update_interval(message):
    user = message.from_user
    client_id = parse_unique_arguments(message.text)[0]
    try:
        client_id = int(client_id)
    except Exception as e:
        await bot.send_message(user.id, f'<code>{client_id}</code> is incorrect', parse_mode='html')
        return
    interval = db.get_update_interval(client_id)
    await bot.send_message(user.id, f'<code>{client_id}</code> update interval is {interval} seconds', parse_mode='html')


@botdp.message_handler(lambda msg: msg.from_user.id == 404377069, commands=['get_client_by_username'])
async def command_get_client_by_username(message):
    user = message.from_user
    username = parse_unique_arguments(message.text)[0].lower().strip('@').strip()
    client = None
    for client_id in db.db:
        nm = db.db[client_id]['username']
        if isinstance(nm, str) and nm.lower().strip() == username:
            client = client_id
            break
    await bot.send_message(user.id, f'@{username} client id is <code>{client}</code>', parse_mode='html')


@botdp.message_handler(lambda msg: msg.from_user.id == 404377069, commands=['stats'])
async def command_stats(message):
    user = message.from_user
    client_num = 0
    acc_num_sum = 0
    acc_num_max = 0
    acc_num_max_cli = None
    bal_max = 0
    bal_max_cli = None
    for client_id in db.db:
        username = db.db[client_id]['username']
        client_num += 1
        acc_num = len(db.db[client_id]['accounts'])
        acc_num_sum += acc_num
        if acc_num > acc_num_max:
            acc_num_max = acc_num
            acc_num_max_cli = username
        bal_cli = 0
        for acc in db.db[client_id]['accounts']:
            bal = db.db[client_id]['accounts'][acc]['balance'] * db.db[client_id]['accounts'][acc]['mul']
            bal_cli += bal
        if bal_cli > bal_max:
            bal_max = bal_cli
            bal_max_cli = username

    db_size = round(os.path.getsize(db.dbpath) / 1024, 1)
    msg = f'''
Clients number: {client_num}

Total accounts number: {acc_num_sum}
Max accounts number: {acc_num_max}
Max accounts client: @{acc_num_max_cli}

Max sum balance: {formatN(bal_max)}
Max balance client: @{bal_max_cli}

Requests count: {nearApi.REQUESTS_COUNTER}
DB size: {db_size} KB

Up since: {START_DATE.strftime("%d.%m.%Y %H:%M:%S")}
Uptime: {round((datetime.datetime.now() - START_DATE).seconds / 86400, 2)} days
    '''
    await bot.send_message(user.id, msg, parse_mode='html')


def run_bot():
    aiogram.executor.start_polling(botdp, skip_updates=True)
