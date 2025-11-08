import swapp, swapp.signals
from snakeware.apis.user import SwUser

class HomeApp(swapp.App):
    def __init__(self):
        pass

    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.LC_FRAME:
                app_fetch = swapp.signals.AppSignal(swapp.signals.AppSignal.APPDB_QUERY, {"type": "all"})
                yield app_fetch
                if app_fetch.success:
                    for app in app_fetch.result.get("apps"):
                        if "main" in app.get("entries"):
                            print(f"{app.get("dname", "<app>")} ({app.get("name", "<unknown>")})")
                else:
                    print("Failed to get apps.")
                app_to_try = input("type an app lol > ")
                if app_to_try == "exit":
                    yield swapp.signals.AppSignal(swapp.signals.AppSignal.EXIT_SUCCESS)
                else:
                    yield swapp.signals.AppSignal(swapp.signals.AppSignal.APP_OPEN, {"target": app_to_try})
                    print("Uh oh!")
            case _:
                pass