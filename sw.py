import sys, os, subprocess, json, configparser, random, filecmp, shutil, tarfile
from xml.etree import ElementTree

#define directories
maindir: str = os.path.split(__file__)[0]
appdir: str = os.path.join(maindir, "app")
cfgfile: str = os.path.join(maindir, "sw.cfg")
sbedir: str = os.path.join(maindir, "sbe")
steamlessdir: str = os.path.join(maindir, "steamless")
steamless: str = os.path.join(steamlessdir, "Steamless.CLI.exe")
steamsettingsdir: str = os.path.normpath(os.path.expanduser("~/AppData/Roaming/GSE Saves/settings/"))
steamsettings: dict[str, str] = {
	"config.main": os.path.join(steamsettingsdir, "configs.main.ini"),
	"config.user": os.path.join(steamsettingsdir, "configs.user.ini"),
	"config.app": os.path.join(steamsettingsdir, "configs.app.ini"),
	"config.overlay": os.path.join(steamsettingsdir, "configs.overlay.ini"),
}
sbeallfiles: dict[str, str] = {
	"steam_api": os.path.join(sbedir, "regular", "x32", "steam_api.dll"),
	"steam_api64": os.path.join(sbedir, "regular", "x64", "steam_api64.dll"),
	"steam_api_experimental": os.path.join(sbedir, "experimental", "x32", "steam_api.dll"),
	"steam_api64_experimental": os.path.join(sbedir, "experimental", "x64", "steam_api64.dll"),
	"generate_interfaces": os.path.join(sbedir, "tools", "generate_interfaces", "generate_interfaces_x32.exe"),
	"generate_interfaces64": os.path.join(sbedir, "tools", "generate_interfaces", "generate_interfaces_x64.exe"),
	"lobby_connect": os.path.join(sbedir, "tools", "lobby_connect", "lobby_connect_x32.exe"),
	"lobby_connect64": os.path.join(sbedir, "tools", "lobby_connect", "lobby_connect_x64.exe")
}
sbefiles: dict[str, str] = {}

#library
librarydir: str = os.path.join(maindir, "library")
library_meta = {}
library: list[dict] = []
menus: dict[str, ElementTree.ElementTree] = {}


os.makedirs(librarydir, exist_ok=True)
os.makedirs(steamsettingsdir, exist_ok=True)

#create blank config
if not os.path.exists(cfgfile):
	open(cfgfile, "x").close()

#copy dir
def make_dir_junction(src: str, dst: str) -> None:
	shutil.copytree(src, dst, dirs_exist_ok=True)

#get file paths for files
def get_sbefiles() -> None:
	global cfg
	if cfg.getboolean("sbe", "exp", fallback=False):
		sbefiles.update({
			"steam_api": sbeallfiles.get("steam_api_experimental"),
			"steam_api64": sbeallfiles.get("steam_api64_experimental"),
		})
	else:
		sbefiles.update({
			"steam_api": sbeallfiles.get("steam_api"),
			"steam_api64": sbeallfiles.get("steam_api64"),
		})
	sbefiles.update({
		"generate_interfaces": sbeallfiles.get("generate_interfaces"),
		"generate_interfaces64": sbeallfiles.get("generate_interfaces64"),
		"lobby_connect": sbeallfiles.get("lobby_connect"),
		"lobby_connect64": sbeallfiles.get("lobby_connect64"),
	})

#convert to number
def number_input(ask: str) -> int:
	while True:
		try:
			return int(input(ask))
		except ValueError:
			print("that's not a number, try again.")

#ask for valid username
def input_username_setup():
	uname = ""
	while True:
		uname = input("Enter your username (5-15 chars): ")
		if len(uname) > 15:
			print("Username is too long!")
		elif len(uname) < 5:
			print("Username is too short!")
		elif not uname.isalnum():
			print("Username contains invalid characters!")
		else:
			uname += "_" + str(random.randint(1111,9999))
			print("Your final username: " + uname)
			break
	return uname

#gen settings for games
def generate_steam_settings() -> None:
	global cfg, steamsettings
	user = configparser.ConfigParser()
	if os.path.isfile(steamsettings.get("config.user")):
		user.read(steamsettings.get("config.user"))
	if not user.has_section("user::general"):
		user.add_section("user::general")
	user.set("user::general", "account_name", cfg.get("user", "name"))
	with open(steamsettings.get("config.user"), "w") as cfgtmp:
		user.write(cfgtmp)
	main = configparser.ConfigParser()
	if os.path.isfile(steamsettings.get("config.main")):
		main.read(steamsettings.get("config.main"))
	if not main.has_section("main::stats"):
		main.add_section("main::stats")
	main.set("main::stats", "allow_unknown_stats", "1")
	if not main.has_section("main::connectivity"):
		main.add_section("main::connectivity")
	main.set("main::connectivity", "disable_lan_only", "1")
	if not main.has_section("main::misc"):
		main.add_section("main::misc")
	main.set("main::misc", "enable_steam_preowned_ids", "1")
	with open(steamsettings.get("config.main"), "w") as cfgtmp:
		main.write(cfgtmp)
	overlay = configparser.ConfigParser()
	if os.path.isfile(steamsettings.get("config.overlay")):
		overlay.read(steamsettings.get("config.overlay"))
	if not overlay.has_section("overlay::general"):
		overlay.add_section("overlay::general")
	overlay.set("overlay::general", "enable_experimental_overlay", "1")
	with open(steamsettings.get("config.overlay"), "w") as cfgtmp:
		overlay.write(cfgtmp)

#patch games
#steamless is slow, use option to skip if not needed
def patch_game(gamedir: str, skip_steamless: bool = True) -> None:
	global sbefiles, steamless
	get_sbefiles()
	for dirpath, _, filenames in os.walk(gamedir):
		for filename in filenames:
			if filename == "steam_api.dll":
				if not filecmp.cmp(os.path.join(dirpath, filename), sbefiles.get("steam_api"), shallow=False):
					#print("Patching steam_api...")
					shutil.copyfile(sbefiles.get("steam_api"), os.path.join(dirpath, filename))
			elif filename == "steam_api64.dll":
				if not filecmp.cmp(os.path.join(dirpath, filename), sbefiles.get("steam_api64"), shallow=False):
					#print("Patching steam_api64...")
					shutil.copyfile(sbefiles.get("steam_api64"), os.path.join(dirpath, filename))
			elif filename.endswith(".exe"):
				if not skip_steamless:
					#print("Running Steamless...")
					subprocess.run([steamless, os.path.join(dirpath, filename), "--quiet"], cwd=dirpath, capture_output=True)
					filename_unpacked = filename + ".unpacked.exe"
					if os.path.exists(filename_unpacked):
						shutil.move(os.path.join(dirpath, filename_unpacked), os.path.join(dirpath, filename))
	generate_steam_settings()

def run_game(exec: list, origin: str):
	patch_game(origin)
	generate_steam_settings()
	print("Running game... (if it doesn't work, run the patcher!)")
	subprocess.run(exec, cwd=origin, shell=True)

def dump_game(gamedir: str, game: dict):
	name = game.get("name", "unknown")
	print("Dumping " + name + "...")
	patch_game(gamedir, False)
	with tarfile.open(name + ".swpkg", "w:gz") as dump:
		dump.add(gamedir, name, recursive=True)
	print("Done.")

#save config
def save_config() -> None:
	global cfg, cfgfile, username
	print("Saving config...")
	cfg.set("user", "name", username)
	with open(cfgfile, "w") as cfgtmp:
		cfg.write(cfgtmp)

#build da library
def build_library(verbose: bool = False) -> None:
	global library, librarydir
	library.clear()
	for dirpath, _, filenames in os.walk(librarydir):
		if dirpath == librarydir:
			continue
		for filename in filenames:
			if filename.endswith(".swgame"):
				filename = os.path.join(dirpath, filename)
				with open(filename) as file:
					game: dict = json.load(file)
					game.update({"origin": dirpath})
					library.append(game)
					if verbose:
						print("Added " + game.get("name"))
	dump_library()

def dump_library():
	global library_meta, library, librarydir
	lib_dump = os.path.join(librarydir, "library.db")
	library_meta.update({"library": library})
	with open(lib_dump, "w") as file:
		json.dump(library_meta, file)

def load_library():
	global library_meta, library, librarydir
	lib_dump = os.path.join(librarydir, "library.cache")
	with open(lib_dump, "r") as file:
		library_meta = json.load(file)
	library = library_meta.get("library")
	if not library:
		library = []

#load menus
def load_menus() -> None:
	global librarydir, menus
	for dirpath, _, filenames in os.walk(librarydir):
		for filename in filenames:
			if filename.endswith(".swpage"):
				fullfilename = os.path.join(dirpath, filename)
				tree = ElementTree.parse(fullfilename)
				menus.update({os.path.splitext(filename)[0]: tree})

def build_menu_array(m: str) -> list[dict]:
	global username, library
	menu = menus.get(m)
	res: list[dict] = []
	if not menu:
		raise FileNotFoundError("no menu")
	if menu.getroot().tag != "page":
		raise Exception("not page")
	
	for child in menu.getroot():
		if child.tag == "sw.library.list":
			for game in library:
				element = {"type": "sw.game", "display": game.get("name"), "game": game}
				res.append(element)
		elif child.tag in menus:
			res.extend(build_menu_array(child.tag))
		else:
			element = {"type": child.tag, "display": child.text}
			element.update(child.attrib)
			res.append(element)
	
	return res

def execute_menu(menu: list[dict]):
	global current_menu
	choices: list[dict] = []
	finaldisplay: list[str] = []

	choicetypes = [
		"link",
		"exit",
		"sw.game",
		"sw.game.patch",
		"sw.game.run",
		"sw.game.remove",
		"sw.library.rebuild",
		"sw.setup.enter_username",
		"sw.game.dump",
		"sw.game.install"
	]

	for item in menu:
		item_type = item.get("type")
		if item_type in choicetypes:
			choices.append(item)
			finaldisplay.append(f"[{len(choices)}]: {item.get("display", "<undef>")}")
		else:
			display = item.get("display", "")
			if display:
				finaldisplay.append(display)
	if len(choices) > 0:
		while True:
			print("\n".join(finaldisplay))
			c = number_input("> ")-1
			if c < 0 or c > len(choices)-1:
				print("invalid choice, try again")
				continue
			choice = choices[c]
			choice_type = choice.get("type")
			result = None
			if choice.get("goto_page"):
				result = choice.get("goto_page", "")
			elif choice_type == "link":
				result = choice.get("target", "")
			elif choice_type == "exit":
				sys.exit(0)
			elif choice_type == "sw.library.rebuild":
				print("Rebuilding library database...")
				build_library()
			elif choice_type == "sw.game":
				game: dict = choice.get("game")
				if not game:
					print("Whoops! Something went wrong!")
				result = [
					{"type": "txt", "display": choice.get("display", "<undef>")},
					{"type": "sw.game.run", "display": "Play", "exec": game.get("exec", []), "origin": game.get("origin")},
					{"type": "sw.game.patch", "display": "Run Patcher", "origin": game.get("origin"), "skip_steamless": False},
					{"type": "sw.game.dump", "display": "Dump files", "origin": game.get("origin"), "game": game},
					{"type": "sw.game.remove", "display": "Uninstall", "origin": game.get("origin")},
					{"type": "link", "display": "Back to Library", "target": "library"}
				]
			elif choice_type == "sw.game.run":
				run_game(choice.get("exec", []), choice.get("origin"))
			elif choice_type == "sw.game.install":
				pth = os.path.normpath(input("Paste the path of your swPKG archive: ")) 
				if os.path.isfile(pth) and tarfile.is_tarfile(pth):
					with tarfile.open(pth, "r:gz") as pkg:
						pkg.extractall(librarydir, filter="data")
					build_library()
					print("Installed.")
				else:
					print("error, not good path")
			elif choice_type == "sw.game.dump":
				dump_game(choice.get("origin", []), choice.get("game"))
			elif choice_type == "sw.game.patch":
				print("Patching...")
				patch_game(choice.get("origin"), choice.get("skip_steamless", True))
				print("Done!")
			elif choice_type == "sw.setup.enter_username":
				global username
				username = input_username_setup()
				save_config()
			elif choice_type == "sw.game.remove":
				print("Uninstalling...")
				shutil.rmtree(choice.get("origin"))
				print("Uninstalled!")
				result = "library"
			else:
				print("unknown error occured, sorry!")
			return result
	else:
		print("\n".join(finaldisplay))

#get config
cfg: configparser.ConfigParser = configparser.ConfigParser()
cfg.read(cfgfile)

#setup
if not cfg.getboolean("user", "setup-done", fallback=False):
	print("Welcome to Snakeware!")
	print("Let's get you setup.")
	if not cfg.has_section("user"):
		cfg.add_section("user")

	uname = input_username_setup()

	cfg.set("user", "name", uname)

	cfg.set("user", "setup-done", "yes")

	if not cfg.has_section("sbe"):
		cfg.add_section("sbe")
	cfg.set("sbe", "exp", "no")

	save_config()
#get username for session
username = cfg.get("user", "name")
generate_steam_settings()

print("Welcome " + username + "!")
print("Loading...")

#load useful things
try:
	load_library()
except:
	build_library()
get_sbefiles()
load_menus()

current_menu = build_menu_array("home")
while True:
	menu_result = execute_menu(current_menu)
	if type(menu_result) is str:
		current_menu = build_menu_array(menu_result)
	elif type(menu_result) is list:
		current_menu = menu_result
	