import swpagestd as std # type: ignore

def check_username():
    if std.cfg_read("user", "name"):
        std.navigate("oobe\\firstrun\\finish")

def write_setup_finished_flag():
    std.cfg_write("user", "setup-done", "yes")