EXIT_SUCCESS = 100 # App is gracefully exiting.
EXIT_FAILURE = 101 # App is exiting due to failiure.
APP_OPEN = 201 # App requests a new app be switched to, starting it if it wasn't already running.
APP_REPLACE = 202 # App requests an app to be replaced with this one
# Query the AppDB
# Data: "type" - type of query ['any', 'exact', 'all-apps']; "name" - name to query
# Result: "apps" - array of resulting apps in the form of AppDict
# AppDict: "name" - app name; "dname" - app display name; "desc" - app description; "ver" - app version; "provides" - array of app provides; "entries" - array of app entry points;
APPDB_QUERY = 300
FS_GET_APPSTORAGE = 400
FS_GET_SHAREDSTORAGE = 401

class AppSignal(Exception):
    EXIT_SUCCESS = EXIT_SUCCESS # App is gracefully exiting.
    EXIT_FAILURE = EXIT_FAILURE # App is exiting due to failiure.
    APP_OPEN = APP_OPEN # App requests a new app be switched to, starting it if it wasn't already running.
    APP_REPLACE = APP_REPLACE # App requests an app to be replaced with this one
    # Query the AppDB
    # Data: "type" - type of query ['any', 'exact', 'all-apps']; "name" - name to query
    # Result: "apps" - array of resulting apps in the form of AppDict
    # AppDict: "name" - app name; "dname" - app display name; "desc" - app description; "ver" - app version; "provides" - array of app provides; "entries" - array of app entry points;
    APPDB_QUERY = APPDB_QUERY
    def __init__(self, id: int, data: dict = None):
        super().__init__(f"SIG_{id}")
        self.id: int = id
        self.data: dict = data.copy() if data else {}
        self.success = False
        self.result: dict = {}
