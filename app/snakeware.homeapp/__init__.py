import swapp, swapp.signals, json, pathlib

class HomeApp(swapp.App):
    def __init__(self, entrypoint):
        super().__init__(entrypoint)
        self.current_page = "home"
        self.recent_apps = []

    def _get_storage_dir(self):
        storage_dir_access_test = swapp.signals.AppSignal(swapp.signals.PERMISSIONS_TEST, {"perm": "fs.storage.app"})
        yield storage_dir_access_test
        if storage_dir_access_test.success:
            storage_dir_signal = swapp.signals.AppSignal(swapp.signals.FS_GET_APPSTORAGE)
            yield storage_dir_signal
            if storage_dir_signal.success:
                return pathlib.Path(storage_dir_signal.result.get("folder"))
        else:
            storage_dir_request = swapp.signals.AppSignal(swapp.signals.PERMISSIONS_REQUEST_INSTALL, {"perm": "fs.storage.app"})
            yield storage_dir_request
            if storage_dir_request.success:
                storage_dir_signal = swapp.signals.AppSignal(swapp.signals.FS_GET_APPSTORAGE)
                yield storage_dir_signal
                if storage_dir_signal.success:
                    return pathlib.Path(storage_dir_signal.result.get("folder"))
            else:
                return None

    def _read_state_files(self):
        storage_dir = yield from self._get_storage_dir()
        if not storage_dir:
            self.recent_apps = []
            return
        recentsfile = storage_dir.joinpath("recentapps.json")
        if recentsfile.is_file():
            with open(recentsfile) as recentsf:
                try:
                    self.recent_apps = json.load(recentsf)
                except Exception as e:
                    self.recent_apps = []
        else:
            self.recent_apps = []

    def _save_state_files(self):
        storage_dir = yield from self._get_storage_dir()
        if not storage_dir:
            return
        recentsfile = storage_dir.joinpath("recentapps.json")
        with open(recentsfile, "w") as recentsf:
            try:
                json.dump(self.recent_apps, recentsf)
            except Exception as e:
                print(e)

    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.APP_ACTIVATING:
                self.current_page = "home"
                #for sig in self._read_state_files():
                    #yield sig
                yield self._read_state_files()
            case swapp.AppEvent.APP_DEACTIVATING:
                #for sig in self._save_state_files():
                    #yield sig
                yield self._save_state_files()
            case swapp.AppEvent.APP_PROCESS:
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
                            append_app = True
                            for app in self.recent_apps:
                                if app.get("name") == action[1]:
                                    append_app = False
                                    break
                            
                            if append_app:
                                self.recent_apps.append({"name": action[1], "dname": action[2]})
                            
                            if len(self.recent_apps) > 5:
                                self.recent_apps = self.recent_apps[0:5]
                            #for sig in self._save_state_files():
                                #yield sig
                            yield self._save_state_files()
                            open_app_signal = swapp.signals.AppSignal(swapp.signals.APP_OPEN, {"target": action[1]})
                            yield open_app_signal
                            if not open_app_signal.success:
                                print("Could not open app. Very sad.")
                        elif action[0] == "shutdown":
                            for sig in self._save_state_files():
                                yield sig
                            raise swapp.signals.AppSignal(swapp.signals.EXIT_SUCCESS)
                        elif action[0] == "switch_page":
                            self.current_page = action[1]
                    except ValueError:
                        print("that's probably not a number")
                    except IndexError:
                        print("bruh")
            case _:
                pass

