import swpage3
from . import AppMetadata, AppEntrypoint

def create_call(func_name, *args):
    return (func_name,) + args

class PageHandlerCompat:
    def __init__(self, app_data: AppMetadata):
        self._page_stack = []
        self.current_page = None
        self.cdata: dict = {}
        self.app_data: AppMetadata = app_data
    
    def push_page(self, page, context_vars: dict=None, args: list = None):
        self.cdata.update({"_sw_page_launch_args": args or []})
        cxvar = context_vars.copy() if context_vars else {}
        cxvar.update(self.cdata.get("_ctx_vars", {}))
        scopes = ["std", "swapp.natives"]
        scopes.extend(self.app_data.page_includes)
        scopes.append(self.app_data.name)
        swpage3.element_registry.set_active_scopes(scopes)
        next_page = swpage3.get_renderable(page, var_ctx=cxvar)
        if self.current_page:
            self._page_stack.append(self.current_page)
        self.current_page = next_page
    
    def replace_page(self, page, context_vars: dict=None, args: list = None):
        self.cdata.update({"_sw_page_launch_args": args or []})
        cxvar = context_vars.copy() if context_vars else {}
        cxvar.update(self.cdata.get("_ctx_vars", {}))
        scopes = ["std", "swapp.natives"]
        scopes.extend(self.app_data.page_includes)
        scopes.append(self.app_data.name)
        swpage3.element_registry.set_active_scopes(scopes)
        next_page = swpage3.get_renderable(page, var_ctx=cxvar)
        self.current_page = next_page

    def pop_page(self):
        try:
            self.current_page = self._page_stack.pop()
        except IndexError:
            self.request_exit()
    
    def request_exit(self):
        self._page_stack.clear()
        self.current_page = None
    
    def sw_call(self, func_name, *args):
        self.cdata.setdefault("_sw_page_handler_calls", [])
        self.cdata["_sw_page_handler_calls"].append(create_call(func_name, *args))
        

class AppHandlerCompat:
    _instance = None
    def __init__(self):
        self._app_stack: list[PageHandlerCompat] = []
        self.current_app: PageHandlerCompat = None
        self.cdata: dict = {}
    
    def push_app(self, app: AppMetadata, entrypoint="main", args: list=None, context_vars: dict=None):
        entryp = app.entrypoints.get(entrypoint)
        if entryp is not None:
            if entryp.entry_type != AppEntrypoint.PAGE_ENTRY:
                raise Exception(f"Non-PageEntry entrypoints are not implemented yet.")
            ep = entryp.data
            new_pages = PageHandlerCompat(app)
            new_pages.cdata.update({"_sw_app_launch_args": args or []})
            new_pages.push_page(ep, context_vars)
            if self.current_app:
                self._app_stack.append(self.current_app)
            self.current_app = new_pages
        else:
            raise Exception(f"Entrypoint {entrypoint} not found.")
    
    def replace_app(self, app: AppMetadata, entrypoint="main", args: list=None, context_vars: dict=None):
        entryp = app.entrypoints.get(entrypoint)
        if entryp is not None:
            if entryp.entry_type != AppEntrypoint.PAGE_ENTRY:
                raise Exception(f"Non-PageEntry entrypoints are not implemented yet.")
            ep = entryp.data
            new_pages = PageHandlerCompat(app)
            new_pages.cdata.update({"_sw_app_launch_args": args or []})
            new_pages.push_page(ep, context_vars)
            self.current_app = new_pages
        else:
            raise Exception(f"Entrypoint {entrypoint} not found.")
    
    def pop_app(self):
        try:
            self.current_app = self._app_stack.pop()
        except IndexError:
            self.request_exit()
    
    def request_exit(self):
        self._app_stack.clear()
        self.current_app = None

    def sw_call(self, func_name, *args):
        self.cdata.setdefault("_sw_app_handler_calls", [])
        self.cdata["_sw_app_handler_calls"].append(create_call(func_name, *args))