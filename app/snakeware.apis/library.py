import json, pathlib

library_meta = {}

def get_library() -> list:
	return library_meta.get("library", [])

def get_library_meta() -> list:
	return library_meta

def build_library(librarydir) -> None:
	librarydir = pathlib.Path(librarydir)
	library_meta.setdefault("library", [])
	get_library().clear()
	for dirpath in librarydir.iterdir():
		if dirpath.is_dir():
			for filename in dirpath.iterdir():
				if filename.is_file():
					if filename.suffix == ".swgame" or filename.name == ".swgame":
						filename = dirpath.joinpath(filename)
						with open(filename) as file:
							game: dict = json.load(file)
							if "id" not in game:
								game.update({"id", game.get("name")})
							if "name" not in game:
								game.update({"name", game.get("id")})
							if game.get("id"):
								game.update({"origin": str(dirpath)})
								get_library().append(game)
	dump_library(librarydir)

def dump_library(librarydir: pathlib.Path):
	library_meta.update({"origin": str(librarydir)})
	lib_dump = librarydir.joinpath("library.db")
	with open(lib_dump, "w") as file:
		json.dump(library_meta, file)

def load_library(librarydir: pathlib.Path):
	library_meta.clear()
	lib_dump = librarydir.joinpath("library.db")
	try:
		with open(lib_dump, "r") as file:
			library_meta.update(json.load(file))
			library_meta.update({"origin": str(librarydir)})
	except:
		pass