import swpage3, swapp
from snakeware.apis import library

@swpage3.element()
class ShelfItem:
    def __init__(self, tag, text, attrib, children):
        self.name = attrib.get("name", "<none>")
        self.game_id = attrib.get("game_id", "<none>")
        self.ctx: swpage3.PageContext = None

    def render(self, ctx: swpage3.PageContext):
        self.ctx = ctx
        idx = ctx.register(self.clicked)
        return swpage3.get_renderable(f"[{idx}] {self.name}")
    
    def clicked(self):
        if self.ctx:
            if self.game_id != "<none>" or self.name != "<none>":
                self.ctx.raise_event("gamelibrary.shelfitem.clicked", [self.game_id, self.name])

@swpage3.element()
class GamePage:
    def __init__(self, tag, text, attrib: dict, children):
        self.id = attrib.get("game_id", "<Unknown>")
        self.name = attrib.get("game_name", "<Unknown>")
    
    def run(self, ctx: swpage3.PageContext):
        ctx.page_handler.sw_call("run_game", self.id)
    
    def patch(self, ctx: swpage3.PageContext):
        ctx.page_handler.sw_call("patch_game", self.id)

    def render(self, ctx: swpage3.PageContext):
        ctx.listen_for_ctxevent("Button.run_game.clicked", self.run)
        ctx.listen_for_ctxevent("Button.patch_game.clicked", self.patch)
        return swpage3.PageXML("<Page><VBox>" + 
                               f"<Label text=\"{self.name}\" />" + 
                               f"<Button id=\"run_game\" text=\"Run Game\" />" + 
                               f"<Button id=\"patch_game\" text=\"Run Patcher\" />" + 
                               "<BackButton text=\"Back\" />" + 
                               "</VBox></Page>")

@swpage3.element()
class LibraryShelf:
    def __init__(self, tag, text, attrib, children):
        pass

    def shelf_clicked(self, ctx: swpage3.PageContext, game_id, game_name):
        ctx.page_handler.push_page(GamePage("GamePage", "", {"game_id": game_id, "game_name": game_name}, []))

    def render(self, ctx: swpage3.PageContext):
        shelf: list[ShelfItem] = []
        lib: list[dict] = library.get_library()
        for game in lib:
            game_name = game.get("name")
            game_id = game.get("id")
            shelf.append(ShelfItem("ShelfItem", "", {"name": game_name, "game_id": game_id}, []))
        ctx.listen_for_ctxevent("gamelibrary.shelfitem.clicked", self.shelf_clicked)
        return swpage3.get_renderable(swpage3.elements.VBox("VBox", "", {}, shelf)(ctx)).render(ctx)
