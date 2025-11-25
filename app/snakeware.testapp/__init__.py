import swapp, swapp.signals

class TestingApp(swapp.App):
    def __init__(self, entrypoint, *args):
        super().__init__(entrypoint)

    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.APP_PROCESS:
                buttons = []
                def create_button(act, label):
                    buttons.append(act)
                    print(f"[{len(buttons)}] {label}")
                    return len(buttons)

                print("- Snakeware Test App -")
                print("Wow we can switch apps!")
                create_button(("shutdown",), "Back")

                if len(buttons) > 0:
                    str_input = input("> ")
                    try:
                        int_input = int(str_input)
                        action = buttons[int_input-1]
                        if action[0] == "open_app":
                            open_app_signal = swapp.signals.AppSignal(swapp.signals.APP_START, {"target": action[1]})
                            yield open_app_signal
                            if not open_app_signal.success:
                                print("Could not open app. Very sad.")
                        elif action[0] == "shutdown":
                            raise swapp.signals.AppSignal(swapp.signals.EXIT_SUCCESS)
                    except ValueError:
                        print("that's probably not a number")
                    except IndexError:
                        print("bruh")
            case _:
                pass

