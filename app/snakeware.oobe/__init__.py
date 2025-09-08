import swpage3, uuid
from snakeware.apis.user import SwUser

@swpage3.element()
class SwUserContinue():
    def __init__(self, *args, **kwargs):
        self.enabled = False
        self.username_to_save = ""
        with SwUser("user.json") as userdata:
            userdata.set("uid", str(uuid.uuid4()))

    def enable(self, *args):
        self.enabled = True
        self.username_to_save = args[0]
        print("yes")

    def render(self, ctx: swpage3.PageContext):
        ctx.listen_for_event("username_entered", self.enable)
        with SwUser("user.json") as userdata:
            userdata.set("name", self.username_to_save)
            userdata.set("setup_finished", True)
        if self.enabled:
            return swpage3.PageXML("<VBox><SwitchPageButton path=\"./finish.swpage3\" text=\"Continue\"/></VBox>")
        else:
            return ""