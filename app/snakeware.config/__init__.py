import swpage3

@swpage3.element()
class SwConfigEventListener:
    def __init__(self, tag, text, attrib, children):
        pass

    def rebuild_library(self):
        try:
            from snakeware.apis.library import build_library, get_library_meta
            libmeta = get_library_meta()
            build_library(libmeta.get("origin"))
        except Exception as e:
            print("Failed to rebuild Library.")
            raise

    def reload_apps(self, ctx: swpage3.PageContext):
        try:
            ctx.page_handler.sw_call("reload_apps")
        except:
            print("Failed to rebuild Library.")

    def render(self, ctx: swpage3.PageContext):
        ctx.listen_for_event("Button.rebuild_library.clicked", self.rebuild_library)
        ctx.listen_for_ctxevent("Button.reload_apps.clicked", self.reload_apps)
        return ""