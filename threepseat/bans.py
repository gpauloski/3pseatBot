import os

from tinydb import TinyDB, Query

class Bans:
    def __init__(self, bans_file):
        self.bans_file = bans_file
        if not os.path.exists(os.path.dirname(bans_file)):
            os.makedirs(os.path.dirname(bans_file))
        if not os.path.exists(self.bans_file):
            open(self.bans_file, 'w').close()
        self._db = TinyDB(self.bans_file)
        self._user = Query()

    def get_table(self, guild):
        return self._db.table(guild)

    def get_value(self, guild, name):
        db = self.get_table(guild)
        if not db.search(self._user.name.matches(name)):
            db.insert({'name': name, 'count': 0})
        result = db.search(self._user.name == name)
        user = result.pop(0)
        return user['count']

    def set_value(self, guild, name, value):
        db = self.get_table(guild)
        db.update({'count': value}, self._user.name == name) 

    def add_to_value(self, guild, name, value):
        cur_val = self.get_value(guild, name)
        val = max(0, cur_val + value)
        self.set_value(guild, name, val)
        return val

    def up(self, guild, name):
        val = self.add_to_value(guild, name, 1)
        self.add_to_value(guild, 'server', 1)
        return val
    
    def down(self, guild, name):
        val = self.add_to_value(guild, name, -1)
        self.add_to_value(guild, 'server', -1)
        return val

    def clear(self, guild, name):
        self.set_value(guild, name, 0)
