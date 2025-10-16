import swpage3

swpage3.element_registry.create_scope("swapp.natives")
swpage3.element_registry.push_scope("swapp.natives")

@swpage3.element()
def RestartSnakewareButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("sw_restart")
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def QuitSnakewareButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("sw_quit")
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def BackButton(tag, text, attrib, children):
    def render(ctx):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            if "click_event" in attrib:
                ctx.raise_event(attrib.get("click_event"))
            ctx.page_handler.pop_page()
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def QuitButton(tag, text, attrib, children):
    def render(ctx):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            if "click_event" in attrib:
                ctx.raise_event(attrib.get("click_event"))
            ctx.app_handler.pop_app()
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def SwitchPageButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("switch_page", attrib.get("path"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def SwitchAppButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("switch_app", attrib.get("app"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def ReplacePageButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("replace_page", attrib.get("path"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@swpage3.element()
def ReplaceAppButton(tag, text, attrib, children):
    def render(ctx: swpage3.PageContext):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            ctx.page_handler.sw_call("replace_app", attrib.get("app"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

swpage3.element_registry.pop_scope()