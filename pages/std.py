swinternal = {}

def import_internals(newinternals: dict):
    swinternal.update(newinternals)

def native_call(namespace: tuple, *args, **kwargs):
    native = swinternal
    for ns in namespace:
        native = native.get(ns)
        if not native:
            raise ValueError(f"Invalid Namespace: {namespace}")
    if not callable(native):
        raise ValueError(f"Invalid func: {namespace}")
    return native(*args, **kwargs)

def get_page(ref: bool = False):
    if ref:
        return native_call(("swpage", "get_page_ref"))
    else:
        return native_call(("swpage", "get_page"))

def navigate(page: str):
    native_call(("swpage", "navigate"), page)

def cfg_read(section: str, key: str):
    return native_call(("cfg", "read"), section, key)

def cfg_readint(section: str, key: str):
    return native_call(("cfg", "readint"), section, key)

def cfg_readfloat(section: str, key: str):
    return native_call(("cfg", "readfloat"), section, key)

def cfg_readbool(section: str, key: str):
    return native_call(("cfg", "readbool"), section, key)

def cfg_write(section: str, key: str, value: str):
    native_call(("cfg", "write"), section, key, value)

def user_write(key: str, value: str):
    native_call(("user_data", "write"), key, value)

def user_read(key: str):
    return native_call(("user_data", "read"), key)

def start_snakeware_network():
    native_call(("native", "start_sw_net"))