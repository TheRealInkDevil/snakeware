import swapp, swapp.signals
from snakeware.apis.user import SwUser

class Boot2(swapp.App):
    def __init__(self):
        super().__init__()
    
    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.SW_BOOT:
                print("Please Wait...")
                app_fetch = swapp.signals.AppSignal(swapp.signals.AppSignal.APPDB_QUERY, {"type": "all"})
                yield app_fetch
                if not app_fetch.success:
                    print("BOOT2 Error: Could not query apps.")
                    raise swapp.signals.AppSignal(swapp.signals.AppSignal.EXIT_FAILURE)
                with SwUser("user.json") as user:
                    target_homeapp = user.get("homeapp", "snakeware.homeapp")
                    homeapp = None
                    for app in app_fetch.result.get("apps", []):
                        if app["name"] == target_homeapp:
                            raise swapp.signals.AppSignal(swapp.signals.AppSignal.APP_REPLACE, {"target": target_homeapp, "entry": "launcher"})
                    raise swapp.signals.AppSignal(swapp.signals.AppSignal.EXIT_FAILURE)
            case _:
                raise swapp.signals.AppSignal(swapp.signals.AppSignal.EXIT_FAILURE)
