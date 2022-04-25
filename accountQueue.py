import heapq


class AccountQueue:

    def __init__(self, db):
        self.queue = []
        self.removed = dict()
        self.last_id = 0
        self.db = db
        heapq.heapify(self.queue)
        for user in db.get_users():
            for acc in db.get_accounts(user):
                self.add(user, acc)

    def add(self, user_id, account):
        self.last_id += 1
        next_update = self.db.get_next_update_time(user_id, account)
        heapq.heappush(self.queue, (next_update, user_id, account, self.last_id))

    def remove(self, user_id, account):
        self.removed[(user_id, account)] = self.last_id

    def dump_remove(self):
        while len(self.queue) > 0:
            tm, user_id, account, id = self.queue[0]
            if (user_id, account) not in self.removed:
                break
            removed_id_time = self.removed.get((user_id, account), -1)
            if id <= removed_id_time:
                heapq.heappop(self.queue)
            else:
                break

    def empty(self):
        self.dump_remove()
        return len(self.queue) == 0

    def get_minimal_time(self):
        self.dump_remove()
        return self.queue[0][0]

    def pop(self):
        self.dump_remove()
        element = self.queue[0]
        heapq.heappop(self.queue)
        return element
