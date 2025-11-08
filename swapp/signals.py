class AppSignal(Exception):
    SIG_EXIT_SUCCESS = 100 # App is gracefully exiting.
    SIG_EXIT_FAILURE = 101 # App is exiting due to failiure.
    SIG_SUSPEND = 102 # App is requesting to be suspended.
    SIG_APP_OPEN = 201 # App requests a new app be switched to, starting it if it wasn't already running.
    SIG_APP_SWITCH = 202 # App requests to switch to an open app, failing if the app isn't open.
    SIG_APP_START = 203 # App requests a new instance of an app be started, failing if it cannot be started.
    SIG_APP_START_BACKGROUND = 204 # App requests an app to be started in the background
    SIG_APP_REPLACE = 205 # App requests an app to be replaced with this one
    SIG_APP_SUSPEND = 301 # App requests another app to be suspended.
    SIG_APP_RESUME = 302 # App requests another app to be resumed.
    SIG_APP_CLOSE = 303 # App requests another app to be closed.
    SIG_APP_TERM = 304 # App requests another app to be terminated.
    def __init__(self, id: int, data: dict = None):
        super().__init__(f"SIG_{id}")
        self.id: int = id
        self.data: dict = data.copy() if data else {}
        self.result: dict = {}