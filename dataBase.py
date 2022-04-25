import os
import json
import time


class DataBase:

    def __init__(self, path):
        self.dbpath = path
        self.db = dict()
        if not os.path.isfile(path):
            self.dump()
        else:
            with open(path, 'r') as f:
                raw_db = json.load(f)
            for key in raw_db:
                self.db[int(key)] = raw_db[key]

    def dump(self):
        with open(self.dbpath, 'w') as f:
            json.dump(self.db, f)

    def check_user_registered(self, user_id):
        return user_id in self.db

    def register_user(self, user_id, username):
        self.db[user_id] = {
            'accounts': {},
            'disabled_accounts': {},
            'user_id': user_id,
            'update_interval': 300,
            'username': username
        }
        self.dump()

    def add_account(self, user_id, account):
        accs = self.db[user_id]['accounts']
        disaccs = self.db[user_id]['disabled_accounts']
        if account in accs:
            return False
        if account in disaccs:
            accs[account] = disaccs[account]
            disaccs.pop(account)
            self.dump()
            return True
        accs[account] = {'timestamp': 0, 'balance': None, 'mul': 1.0}
        self.dump()
        return True

    def remove_account(self, user_id, account):
        accs = self.db[user_id]['accounts']
        disaccs = self.db[user_id]['disabled_accounts']
        if account not in accs:
            return False
        disaccs[account] = accs[account]
        # disaccs[account]['balance'] = None
        disaccs[account]['mul'] = 1.0
        accs.pop(account)
        self.dump()
        return True

    def optimize_disabled(self, user_id):
        user = self.db[user_id]
        disaccs = user['disabled_account']
        for acc in disaccs:
            if time.time() - disaccs[acc]['timestamp'] >= user['update_interval']:
                disaccs.pop(acc)
        self.dump()

    def get_users(self):
        return list(self.db.keys())

    def get_accounts(self, user_id):
        return list(self.db[user_id]['accounts'].keys())

    def get_next_update_time(self, user_id, account):
        return self.db[user_id]['update_interval'] + self.db[user_id]['accounts'][account]['timestamp']

    def get_balance(self, user_id, account):
        return self.db[user_id]['accounts'].get(account, {}).get('balance')

    def get_account_mul(self, user_id, account):
        return self.db[user_id]['accounts'].get(account, {}).get('mul')

    def update_balance(self, user_id, account, balance, timestamp):
        self.db[user_id]['accounts'][account]['balance'] = balance
        self.db[user_id]['accounts'][account]['timestamp'] = timestamp
        self.dump()

    def set_account_mul(self, user_id, account, mul):
        accounts = self.db[user_id]['accounts']
        if account not in accounts:
            return False
        accounts[account]['mul'] = mul
        self.dump()
        return True

    def check_account_validated(self, user_id, account):
        active = account in self.db[user_id]['accounts']
        disabled = account in self.db[user_id]['disabled_accounts']
        return active or disabled

    def get_update_interval(self, user_id):
        return self.db.get(user_id, {}).get('update_interval')

    def set_update_interval(self, user_id, update_interval):
        self.db[user_id]['update_interval'] = update_interval
        self.dump()
