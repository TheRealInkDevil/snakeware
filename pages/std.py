swinternal = {}

def import_internals(newinternals: dict):
    swinternal.update(newinternals)

def get_page(ref: bool = False):
    global swinternal
    if ref:
        return swinternal["swpage"]["get_page_ref"]()
    else:
        return swinternal["swpage"]["get_page"]()

def navigate(page: str):
    global swinternal
    swinternal["swpage"]["navigate"](page)

def cfg_read(section: str, key: str):
    return swinternal["cfg"]["read"](section, key)

def cfg_readint(section: str, key: str):
    return swinternal["cfg"]["readint"](section, key)

def cfg_readfloat(section: str, key: str):
    return swinternal["cfg"]["readfloat"](section, key)

def cfg_readbool(section: str, key: str):
    return swinternal["cfg"]["readbool"](section, key)

def cfg_write(section: str, key: str, value: str):
    swinternal["cfg"]["write"](section, key, value)

def user_write(key: str, value: str):
    swinternal["user_data"]["write"](key, value)

def user_read(key: str):
    swinternal["user_data"]["read"](key)

def start_snakeware_network():
    swinternal["native"]["start_sw_net"]()

def native_call(namespace: tuple, *args, **kwargs):
    native = swinternal.copy()
    for ns in namespace:
        native = native.get(ns)
        if not native:
            raise ValueError("INVALID NAMESPACE")
    native(*args, **kwargs)