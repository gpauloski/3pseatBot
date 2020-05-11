import os

from tinydb import TinyDB, Query

class Bans:
    def __init__(self):
        self.bans_file = 'bans.json'
        if not os.path.exists(self.bans_file):
            open(self.bans_file, 'a').close()
        self._db = TinyDB(self.bans_file)
        self._user = Query()

    def get_table(self, guild):
        return self._db.table(guild)

    def check(self, guild, name):
        db = self.get_table(guild)
        if not db.search(self._user.name.matches(name)):
            db.insert({'name': name, 'count': 0})
        result = db.search(self._user.name == name)
        user = result.pop(0)
        return user['count']

    def up(self, guild, name):
        db = self.get_table(guild)
        # Add 1 to user count
        val_user = self.check(guild, name) + 1
        db.update({'count': val_user}, self._user.name == name)
        # Add 1 to guild count
        val_server = self.check(guild, 'guild') + 1
        db.update({'count': val_server}, self._user.name == 'guild')
        return val_user

    def clear(self, guild, name):
        db = self.get_table(guild)
        self.check(guild, name)
        db.update({'count': 0}, self._user.name == name)
