import types

class AppMetadata:
    def __init__(self, origin):
        self.db: AppDB = None
        self.name: str = "<name>"
        self.display_name: str = "<display_name>"
        self.version: str = "<version>"
        self.desc: str = "<description>"
        self.modules: dict[str, types.ModuleType] = {}
        self.entrypoints: dict[str, AppEntrypoint] = {}
        self.origin: str = origin
        self.page_includes: list[str] = []
        self.provides: list[str] = []
    
    def copy(self, *, include_entrypoints: bool = True, include_ref_types: bool = False):
        result = AppMetadata()
        result.name = self.name
        result.display_name = self.display_name
        result.version = self.version
        result.desc = self.desc
        result.origin = self.origin
        result.page_includes = self.page_includes.copy()
        if include_entrypoints:
            for key, value in self.entrypoints.items():
                result.entrypoints.update({key: value.copy()})
        if include_ref_types:
            result.modules = self.modules.copy()
        return result


class AppEntrypoint:
    CLASS_ENTRY = 0
    FUNC_ENTRY = 1
    PAGE_ENTRY = 2
    def __init__(self, id: str, entry_type: int, data):
        self.id: str = id
        self.data = data
        self.entry_type: int = entry_type
    
    def copy(self):
        result = AppEntrypoint(self.id, self.entry_type, self.data)
        return result

class AppEvent:
    SW_BOOT = -1 # Boot App Startup
    LC_START = 0 # App Startup (before LC_ENTERING_FOREGROUND and LC_ENTERING_BACKGROUND)
    LC_FRAME = 1 # App Frame Update
    LC_BACKGROUND_UPDATE = 2 # Background App Tick
    LC_RESUMING = 3 # App is Resuming
    LC_SUSPENDING = 4 # App is Pausing (Suspending)
    LC_ENTERING_BACKGROUND = 5 # App is entering background, leaving foreground
    LC_ENTERING_FOREGROUND = 6 # App is entering foreground, leaving background
    LC_CLOSE = 7 # Close has been requested
    LC_TERMINATING = 8 # App is about to be killed
    LC_CLOSING = 9 # App is about to be killed

    def __init__(self, type: int, data: dict):
        self.type: int = type
        self.data: dict = data.copy() if data else dict()

class App:
    def __init__(self):
        pass

    def ev_signal(self, event: AppEvent):
        pass

APPSTATUS_NONE = 000
APPSTATUS_BOOTING = 100
APPSTATUS_STARTING = 101
APPSTATUS_ENTERING_FOREGROUND = 102
APPSTATUS_FOREGROUND = 103
APPSTATUS_BACKGROUND_STARTING = 201
APPSTATUS_ENTERING_BACKGROUND = 202
APPSTATUS_BACKGROUND = 203
APPSTATUS_EXITED_SUCCESS = 400
APPSTATUS_EXITED_FAILURE = 401

class RunningApp:
    def __init__(self, app: App, app_metadata: AppMetadata):
        self.app: App = app
        self.app_metadata: AppMetadata = app_metadata
        self.status: int = APPSTATUS_NONE

class AppStack:
    def __init__(self):
        self.running: list[RunningApp] = []
    
    def add_to_stack(self, app: RunningApp):
        self.running.append(app)

    def get_app_by_name(self, name):
        for app in self.running:
            if app.app_metadata.name == name:
                return app
        return None

    def get_apps_by_name(self, name):
        result = []
        for app in self.running:
            if app.app_metadata.name == name:
                result.append(app)
        return result

class AppDB:
    def __init__(self):
        self.apps: dict[str, AppMetadata] = {}
        self.provided: dict[str, dict[str, AppMetadata]] = {}
    
    def __contains__(self, value):
        return value in self.apps or value in self.provided
    
    def add_app(self, new_app: AppMetadata):
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
                return next(iter(self.provided[app].keys()), None)
        return None
    
    def get_app(self, name, ignore_provides=False):
        if ignore_provides:
            return self.apps.get(name, None)
        return self.apps.get(self.resolve_app_name(name), None)

    def by_name(self, name, include_provides=False):
        result: list[AppMetadata] = {}
        for app in self.apps.values():
            if app.name == name or (include_provides and name in app.provides):
                result.append(app)
    
    def by_entry(self, name):
        result: list[AppMetadata] = {}
        for app in self.apps.values():
            if name in app.entrypoints:
                result.append(app)