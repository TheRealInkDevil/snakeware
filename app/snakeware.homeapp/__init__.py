import swapp, swapp.signals
from snakeware.apis.user import SwUser

class HomeApp(swapp.App):
    def __init__(self):
        self.current_page = "home"
        self.recent_apps = []

    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.LC_ENTERING_FOREGROUND:
                self.current_page = "home"
                with SwUser("user.json") as user:
                    self.recent_apps = user.get("snakeware.homeapp.recentapps", [])
            case swapp.AppEvent.LC_FRAME:
                buttons = []
                def create_button(act, label):
                    buttons.append(act)
                    print(f"[{len(buttons)}] {label}")
                    return len(buttons)
                match self.current_page:
                    case "home":
                        print("Recent Apps:")
                        for pin in self.recent_apps:
                            create_button(("open_app", pin.get("name", "<name>")), pin.get("dname", "<dname>"))
                        print("- -")
                        create_button(("switch_page", "all-apps"), "View all Apps")
                        create_button(("shutdown",), "Quit")
                    case "all-apps":
                        app_fetch = swapp.signals.AppSignal(swapp.signals.APPDB_QUERY)
                        yield app_fetch
                        if not app_fetch.success:
                            print("Could not fetch apps.")
                        else:
                            print("All Apps:")
                            for pin in app_fetch.result.get("apps"):
                                if "main" in pin.get("entries", []):
                                    create_button(("open_app_w_dname", pin.get("name", "<name>"), pin.get("dname", "<dname>")), pin.get("dname", "<dname>"))
                            create_button(("switch_page", "home"), "Back")

                if len(buttons) > 0:
                    str_input = input("> ")
                    try:
                        int_input = int(str_input)
                        action = buttons[int_input-1]
                        if action[0] == "open_app":
                            open_app_signal = swapp.signals.AppSignal(swapp.signals.APP_OPEN, {"target": action[1]})
                            yield open_app_signal
                            if not open_app_signal.success:
                                print("Could not open app. Very sad.")
                        if action[0] == "open_app_w_dname":
                            with SwUser("user.json") as user:
                                self.recent_apps.append({"name": action[1], "dname": action[2]})
                                if len(self.recent_apps) > 5:
                                    self.recent_apps = recent_apps[0:5]
                                user.set("snakeware.homeapp.recentapps", self.recent_apps)
                            open_app_signal = swapp.signals.AppSignal(swapp.signals.APP_OPEN, {"target": action[1]})
                            yield open_app_signal
                            if not open_app_signal.success:
                                print("Could not open app. Very sad.")
                        elif action[0] == "shutdown":
                            raise swapp.signals.AppSignal(swapp.signals.EXIT_SUCCESS)
                        elif action[0] == "switch_page":
                            self.current_page = action[1]
                    except ValueError:
                        print("that's probably not a number")
                    except IndexError:
                        print("bruh")
            case _:
                pass

