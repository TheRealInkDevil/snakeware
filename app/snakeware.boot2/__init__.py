import swpage3
from snakeware.apis import user

@swpage3.element()
def LaunchOOBEIfNeeded(*args, **kwargs):
    redirect = None
    with user.SwUser("user.json") as userdata:
        if not userdata.get("setup_finished", False):
            def redir(ctx: swpage3.PageContext):
                ctx.page_handler.sw_call("replace_app", "snakeware.oobe")
                return ""
            return redir
        else:
            def redir(ctx: swpage3.PageContext):
                ctx.page_handler.sw_call("replace_app", "snakeware.homeapp")
                return ""
            return redir