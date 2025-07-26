import std, uuid

def genuserdat():
    userid = uuid.uuid4()
    std.user_write("uid", str(userid))

def enableswnetwork():
    std.user_write("sw_network_enabled", True)
    std.start_snakeware_network()