import swapp, swapp.signals
from snakeware.apis import user

class Boot2(swapp.App):
    def __init__(self):
        super().__init__()
    
    def ev_signal(self, event):
        match event.type:
            case swapp.AppEvent.SW_BOOT:
                print("Please Wait...")
                raise swapp.signals.AppSignal(swapp.signals.AppSignal.SIG_APP_REPLACE, {"target": "snakeware.homeapp"})
            case _:
                raise swapp.signals.AppSignal(swapp.signals.AppSignal.SIG_EXIT_FAILURE)