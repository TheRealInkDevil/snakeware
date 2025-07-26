def check_username():
    global cfg_read, navigate
    if cfg_read("user", "name"):
        navigate("oobe\\firstrun\\finish")