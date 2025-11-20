import swapp, swapp.signals

class Boot2(swapp.App):
    def __init__(self, entrypoint, *args):
        super().__init__(entrypoint)
    
    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.SNAKEWARE_BOOTUP:
                print("Please Wait...")
                app_fetch = swapp.signals.AppSignal(swapp.signals.APPDB_QUERY, {"type": "all"})
                yield app_fetch
                if not app_fetch.success:
                    print("BOOT2 Error: Could not query apps.")
                    raise swapp.signals.AppSignal(swapp.signals.EXIT_FAILURE)
                target_homeapp = "snakeware.homeapp"
                
                for app in app_fetch.result.get("apps", []):
                    if app["name"] == target_homeapp:
                        raise swapp.signals.AppSignal(swapp.signals.APP_REPLACE, {"target": target_homeapp, "entry": "launcher"})
                raise swapp.signals.AppSignal(swapp.signals.EXIT_FAILURE)
            case _:
                raise swapp.signals.AppSignal(swapp.signals.EXIT_FAILURE)
