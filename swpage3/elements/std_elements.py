from .. import element, get_renderable

@element()
def Label(tag, text, attrib, children):
    def render(ctx):
        return attrib.get("text", "")
    return render

@element()
def Header(tag, text, attrib, children):
    new_attrib = attrib.copy()
    dash_count = int(attrib.get("count")) if "count" in attrib else 1
    new_attrib.update({"text": ("-"*dash_count) + " " + attrib.get("text", "") + " " + ("-"*dash_count)})
    return Label(tag, text, new_attrib, children)

@element()
def Button(tag, text, attrib, children):
    def render(ctx):
        def clicked():
            if "id" in attrib:
                if "class" in attrib:
                    ctx.raise_event(f"{tag}.{attrib.get("class")}.{attrib.get("id")}.clicked")
                else:
                    ctx.raise_event(f"{tag}.{attrib.get("id")}.clicked")
            if "click_event" in attrib:
                ctx.raise_event(attrib.get("click_event"))
        idx = ctx.register(clicked)
        return f"[{idx}] {attrib.get("text", "")}"
    return render

@element()
def VBox(tag, text, attrib, children):
    def render(ctx):
        stack = "\n".join([get_renderable(child.render(ctx)).render(ctx) for child in children])
        stack = stack.strip()
        return stack
    return render

@element()
def Page(tag, text, attrib, children):
    def render(ctx):
        stack = "".join([get_renderable(child.render(ctx)).render(ctx) for child in children])
        stack = stack.strip()
        return stack
    return render

@element()
def HBox(tag, text, attrib, children):
    def render(ctx):
        stack = " ".join([get_renderable(child.render(ctx)).render(ctx) for child in children])
        stack = stack.strip()
        return stack
    return render

@element()
class TextBox:
    def __init__(self, tag, text, attrib, children):
        self.tag = tag
        self.attrib = attrib
        self.input = ""
        self.ctx = None
    
    def clicked(self):
        if "prompt" in self.attrib:
            self.input = input(f"{self.attrib.get("prompt")} > ")
        else:
            self.input = input("Enter input: > ")
        if "id" in self.attrib:
            if "class" in self.attrib:
                self.ctx.raise_event(f"{self.tag}.{self.attrib.get("class")}.{self.attrib.get("id")}.updated", args=[self.input])
            else:
                self.ctx.raise_event(f"{self.tag}.{self.attrib.get("id")}.updated", args=[self.input])
        if "update_event" in self.attrib:
            self.ctx.raise_event(self.attrib.get("update_event"), args=[self.input])

    def render(self, ctx):
        self.ctx = ctx
        idx = ctx.register(self.clicked)
        return f"[{idx}] {self.attrib.get("text")} <{self.input}>" if self.input else f"[{idx}] {self.attrib.get("text")}"