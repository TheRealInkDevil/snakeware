import swpage3


class App:
    def __init__(self, origin):
        self.db: AppDB = None
        self.name = "<name>"
        self.display_name = "<display_name>"
        self.version = "<version>"
        self.desc = "<description>"
        self.modules = {}
        self.entrypoints = {}
        self.origin = origin
        self.page_includes = []
        self.provides = []

def create_call(func_name, *args):
    return (func_name,) + args

class AppDB:
    def __init__(self):
        self.apps: dict[str, App] = {}
        self.provided: dict[str, dict[str, App]] = {}
    
    def __contains__(self, value):
        return value in self.apps or value in self.provided
    
    def add_app(self, new_app: App):
        if new_app.name not in self.apps:
            self.apps[new_app.name] = new_app
        for provide in new_app.provides:
            self.provided.setdefault(provide, {}).update({new_app.name: new_app})
    
    def resolve_app_name(self, name):
        for app in self.apps:
            if app == name:
                return app
        for app in self.provided:
            if app == name:
                return next(iter(self.provided[app].values()), None)
        return None
    
    def get_app(self, name, ignore_provides=False):
        if ignore_provides:
            return self.apps.get(name, None)
        return self.apps.get(self.resolve_app_name(name), None)

    def by_name(self, name, include_provides=False):
        result: list[App] = {}
        for app in self.apps.values():
            if app.name == name or (include_provides and name in app.provides):
                result.append(app)
    
    def by_entry(self, name):
        result: list[App] = {}
        for app in self.apps.values():
            if name in app.entrypoints:
                result.append(app)

class PageHandler:
    def __init__(self, app_data: App):
        self._page_stack = []
        self.current_page = None
        self.cdata: dict = {}
        self.app_data: App = app_data
    
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
        

class AppHandler:
    _instance = None
    def __init__(self):
        self._app_stack: list[PageHandler] = []
        self.current_app: PageHandler = None
        self.cdata: dict = {}
    
    def push_app(self, app: App, entrypoint="main", args: list=None, context_vars: dict=None):
        ep = app.entrypoints.get(entrypoint)
        if ep is not None:
            new_pages = PageHandler(app)
            new_pages.cdata.update({"_sw_app_launch_args": args or []})
            new_pages.push_page(ep, context_vars)
            if self.current_app:
                self._app_stack.append(self.current_app)
            self.current_app = new_pages
        else:
            raise Exception(f"Entrypoint {entrypoint} not found.")
    
    def replace_app(self, app: App, entrypoint="main", args: list=None, context_vars: dict=None):
        ep = app.entrypoints.get(entrypoint)
        if ep is not None:
            new_pages = PageHandler(app)
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

swpage3.element_registry.create_scope("swapp.natives")
swpage3.element_registry.push_scope("swapp.natives")

@swpage3.element()
def RestartSnakewareButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("sw_restart")
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def QuitSnakewareButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("sw_quit")
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def BackButton(tag, text, attrib, children):
    def render(ctx):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            if "click_event" in attrib:
                ctx.raise_event(attrib.get("click_event"))
            ctx.page_handler.pop_page()
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def QuitButton(tag, text, attrib, children):
    def render(ctx):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            if "click_event" in attrib:
                ctx.raise_event(attrib.get("click_event"))
            ctx.app_handler.pop_app()
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def SwitchPageButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("switch_page", attrib.get("path"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def SwitchAppButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("switch_app", attrib.get("app"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def ReplacePageButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("replace_page", attrib.get("path"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def ReplaceAppButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("replace_app", attrib.get("app"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

swpage3.element_registry.pop_scope()