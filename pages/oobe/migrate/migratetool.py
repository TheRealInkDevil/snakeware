import std

def migrateusername():
    if std.cfg_read("user", "name"):
        std.user_write("name", std.cfg_read("user", "name"))