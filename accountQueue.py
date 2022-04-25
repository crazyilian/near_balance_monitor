from sortedcontainers import SortedSet


class AccountQueue:

    def __init__(self, db):
        self.queue = SortedSet()
        self.next_upd = dict()
        self.db = db
        for user in db.get_users():
            for acc in db.get_accounts(user):
                self.add(user, acc)

    def add(self, user_id, account):
        next_update = self.db.get_next_update_time(user_id, account)
        self.next_upd[(user_id, account)] = next_update
        self.queue.add((next_update, user_id, account))

    def remove(self, user_id, account):
        next_update = self.next_upd[(user_id, account)]
        self.queue.remove((next_update, user_id, account))
        self.next_upd.pop((user_id, account))

    def empty(self):
        return len(self.queue) == 0

    def get_minimal_time(self):
        element = next(iter(self.queue))
        return element[0]

    def pop(self):
        element = self.queue.pop(0)
        self.next_upd.pop((element[1], element[2]))
        return element
