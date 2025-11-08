import swapp, swapp.signals

class HomeApp(swapp.App):
    def __init__(self):
        pass

    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.LC_FRAME:
                input("Yay it works! > ")
            case _:
                print("Unhandled Event.")