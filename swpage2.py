import pathlib
from xml.etree import ElementTree

class Page:
    def __init__(self, name: str, modulename: str, location: pathlib.Path, file: str, tree: ElementTree.ElementTree):
        self.name = name
        self.modulename = modulename
        self.location = pathlib.Path(location)
        self.file = file
        self.tree = tree

class PageManager:
    def __init__(self):
        self.pages: list[Page] = []
        self.by_name: dict[str, Page] = {}
        self.by_modulename: dict[str, Page] = {}
        self.by_location: dict[str, Page] = {}
        self.by_file: dict[str, Page] = {}
    
    def build_sort(self):
        self.by_name.clear()
        self.by_modulename.clear()
        self.by_location.clear()
        self.by_file.clear()
        for page in self.pages:
            self.by_name.update({page.name: page})
            self.by_modulename.update({page.modulename: page})
            self.by_location.update({page.location: page})
            self.by_file.update({page.file: page})

    def add(self, page: Page):
        self.pages.append(page)
        self.build_sort()