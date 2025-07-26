#core imports
import sys, os, subprocess, json, configparser, random, filecmp, shutil, tarfile, zipfile, builtins, types, pathlib
from xml.etree import ElementTree
#define core directory
maindir: pathlib.Path = pathlib.Path(__file__).parent
sys.path.append(str(maindir))

#critical imports
import swpage2

#define other directories
appdir: pathlib.Path = maindir.joinpath("app")
cfgfile: pathlib.Path = maindir.joinpath("sw.cfg")
userfile: pathlib.Path = maindir.joinpath("user.json")
sbedir: pathlib.Path = maindir.joinpath("sbe")
steamlessdir: pathlib.Path = maindir.joinpath("steamless")
steamless: pathlib.Path = steamlessdir.joinpath("Steamless.CLI.exe")
steamsettingsdir: pathlib.Path = pathlib.Path(pathlib.Path.home(), "AppData/Roaming/GSE Saves/settings/")
steamsettings: dict[str, pathlib.Path] = {
	"config.main": steamsettingsdir.joinpath("configs.main.ini"),
	"config.user": steamsettingsdir.joinpath("configs.user.ini"),
	"config.app": steamsettingsdir.joinpath("configs.app.ini"),
	"config.overlay": steamsettingsdir.joinpath("configs.overlay.ini"),
}
sbeallfiles: dict[str, pathlib.Path] = {
	"steam_api": sbedir.joinpath("regular", "x32", "steam_api.dll"),
	"steam_api64": sbedir.joinpath("regular", "x64", "steam_api64.dll"),
	"steam_api_experimental": sbedir.joinpath("experimental", "x32", "steam_api.dll"),
	"steam_api64_experimental": sbedir.joinpath("experimental", "x64", "steam_api64.dll"),
	"generate_interfaces": sbedir.joinpath("tools", "generate_interfaces", "generate_interfaces_x32.exe"),
	"generate_interfaces64": sbedir.joinpath("tools", "generate_interfaces", "generate_interfaces_x64.exe"),
	"lobby_connect": sbedir.joinpath("tools", "lobby_connect", "lobby_connect_x32.exe"),
	"lobby_connect64": sbedir.joinpath("tools", "lobby_connect", "lobby_connect_x64.exe")
}
sbefiles: dict[str, pathlib.Path] = {}

#library and pages/menus
librarydir: pathlib.Path = maindir.joinpath("library")
pagedir: pathlib.Path = maindir.joinpath("pages")
pagestdpth: pathlib.Path = pagedir.joinpath("std.py")
pagestd = {}
pagestdmod: types.ModuleType = None
library_meta = {}
library: list[dict] = []
pagemgr: swpage2.PageManager = swpage2.PageManager()
menus: dict[str, ElementTree.ElementTree] = {}
launch_option = "quit"

LAUNCHER_NAME = "<none>"
LAUNCHER_TYPE = "self"

os.makedirs(librarydir, exist_ok=True)
os.makedirs(steamsettingsdir, exist_ok=True)

#try to detect current launcher
#returns launcher as the following: (type, name, version)
def detect_launcher():
	if os.getenv("FASTBOOT_BOOTLOADER_NAME"):
		return ("fastboot", os.getenv("FASTBOOT_BOOTLOADER_NAME"), os.getenv("FASTBOOT_BOOTLOADER_VERSION"))
	else:
		return ("self", "<none>", 0)

def run_fastboot_command(args: list[str], wait: bool = True):
	arg = [os.getenv("FASTBOOT_PYTHON"), os.getenv("FASTBOOT_SRC")]
	arg.extend(args)
	proc = subprocess.Popen(arg)
	if wait:
		proc.wait()
	return proc.returncode

#create blank config
if not cfgfile.exists():
	open(cfgfile, "x").close()

def quit():
	if LAUNCHER_TYPE == "fastboot":
		sys.exit(0)
	else:
		sys.exit(0)

def restart():
	if LAUNCHER_TYPE == "fastboot":
		subprocess.Popen([os.getenv("FASTBOOT_PYTHON"), os.getenv("FASTBOOT_SRC")])
		sys.exit(0)
	else:
		subprocess.Popen(sys.orig_argv)
		sys.exit(0)
		

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
	if steamsettings.get("config.user").is_file():
		user.read(steamsettings.get("config.user"))
	if not user.has_section("user::general"):
		user.add_section("user::general")
	user.set("user::general", "account_name", cfg.get("user", "name"))
	with open(steamsettings.get("config.user"), "w") as cfgtmp:
		user.write(cfgtmp)
	main = configparser.ConfigParser()
	if steamsettings.get("config.main").is_file():
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
	if steamsettings.get("config.overlay").is_file():
		overlay.read(steamsettings.get("config.overlay"))
	if not overlay.has_section("overlay::general"):
		overlay.add_section("overlay::general")
	overlay.set("overlay::general", "enable_experimental_overlay", "1")
	with open(steamsettings.get("config.overlay"), "w") as cfgtmp:
		overlay.write(cfgtmp)

#patch games
#steamless is slow, use option to skip if not needed
def patch_game(gamedir: pathlib.Path, skip_steamless: bool = True) -> None:
	global sbefiles, steamless
	gamedir = pathlib.Path(gamedir)
	get_sbefiles()
	for dirpath, _, filenames in gamedir.walk():
		for filename in filenames:
			if filename == "steam_api.dll":
				if not filecmp.cmp(dirpath.joinpath(filename), sbefiles.get("steam_api"), shallow=False):
					#print("Patching steam_api...")
					shutil.copyfile(sbefiles.get("steam_api"), dirpath.joinpath(filename))
			elif filename == "steam_api64.dll":
				if not filecmp.cmp(dirpath.joinpath(filename), sbefiles.get("steam_api64"), shallow=False):
					#print("Patching steam_api64...")
					shutil.copyfile(sbefiles.get("steam_api64"), dirpath.joinpath(filename))
			elif filename.endswith(".exe"):
				if not skip_steamless:
					#print("Running Steamless...")
					subprocess.run([steamless, dirpath.joinpath(filename), "--quiet"], cwd=dirpath, capture_output=True)
					filename_unpacked = dirpath.joinpath(filename + ".unpacked.exe")
					if filename_unpacked.exists():
						shutil.move(dirpath.joinpath(filename_unpacked), dirpath.joinpath(filename))
	generate_steam_settings()

def run_game(exec: list, origin: str):
	patch_game(origin)
	generate_steam_settings()
	print("Running game... (if it doesn't work, run the patcher!)")
	subprocess.run(exec, cwd=origin, shell=True)

def dump_game_tar(gamedir: str, game: dict):
	name = game.get("name", "unknown")
	print("Dumping " + name + "...")
	patch_game(gamedir, False)
	with tarfile.open(name + ".swpkg", "w:gz") as dump:
		dump.add(gamedir, name, recursive=True)
	print("Done.")

def dump_game_zip(gamedir: pathlib.Path, game: dict):
	gamedir = pathlib.Path(gamedir)
	name = game.get("name", "unknown")
	print("Dumping " + name + "...")
	patch_game(gamedir, False)
	with zipfile.ZipFile(name + ".swpkg", "w") as dump:
		for root, dirs, files in gamedir.walk():
			for file in files:
				dump.write(root.joinpath(file), pathlib.Path(name, root.joinpath(file).relative_to(gamedir)))
	print("Done.")

#save config
def save_config() -> None:
	global cfg, cfgfile, username
	if not cfg.has_section("user"):
		cfg.add_section("user")
	cfg.set("user", "name", username)
	with open(cfgfile, "w") as cfgtmp:
		cfg.write(cfgtmp)

#build da library
def build_library(verbose: bool = False) -> None:
	global library, librarydir
	library.clear()
	for dirpath, _, filenames in librarydir.walk():
		if dirpath == librarydir:
			continue
		for filename in filenames:
			if filename.endswith(".swgame"):
				filename = dirpath.joinpath(filename)
				with open(filename) as file:
					game: dict = json.load(file)
					game.update({"origin": str(dirpath)})
					library.append(game)
					if verbose:
						print("Added " + game.get("name"))
	dump_library()

def dump_library():
	global library_meta, library, librarydir
	lib_dump = librarydir.joinpath("library.db")
	library_meta.update({"library": library})
	with open(lib_dump, "w") as file:
		json.dump(library_meta, file)

def load_library():
	global library_meta, library, librarydir
	lib_dump = librarydir.joinpath("library.db")
	with open(lib_dump, "r") as file:
		library_meta = json.load(file)
	library = library_meta.get("library")
	if not library:
		library = []

def compile_pagestd():
	global pagestd, pagestdpth, pagestdmod
	try:
		with open(pagestdpth) as file:
			pagestdcode = compile(file.read(), pagestdpth, "exec")
			exec(pagestdcode, pagestd)
			pagestdmod = types.ModuleType("swpagestd")
			for key, value in pagestd.items():
				setattr(pagestdmod, key, value)
			sys.modules["swpagestd"] = pagestdmod
	except:
		print("SWPAGE Standard Library could not be compiled!")
		raise

#load menus
def load_menus() -> None:
	global pagedir, menus, pagemgr
	for dirpath, _, filenames in pagedir.walk():
		for filename in filenames:
			if filename.endswith(".swpage") or filename.endswith(".html"):
				fullfilename = dirpath.joinpath(filename)
				tree = ElementTree.parse(fullfilename)
				if filename == "index.html":
					pth = dirpath.relative_to(pagedir)
					menus.update({pth: tree})
					pagemgr.add(swpage2.Page(str(pth), str(pth.with_suffix("")), dirpath, str(fullfilename), tree))
				else:
					pth = fullfilename.relative_to(pagedir)
					menus.update({pth: tree})
					pagemgr.add(swpage2.Page(str(pth), str(pth.with_suffix("")), dirpath, str(fullfilename), tree))

def get_menu_root(m: str | ElementTree.ElementTree) -> ElementTree.Element:
	global pagemgr
	if type(m) is str:
		menu = pagemgr.by_modulename.get(m).tree
		if not menu:
			raise FileNotFoundError("no menu")
	else:
		menu = m
	
	root = menu.getroot()
	if root.tag == "page":
		return root
	elif root.tag == "html":
		for child in root:
			if child.tag == "body":
				return root
		raise Exception("HTML-SWPAGE: no body")
	else:
		raise Exception("not compatible menu")
	
def build_menu_array(m, parentpage: swpage2.Page = None) -> list[dict]:
	global username, library, pagedir, pagemgr
	res: list[dict] = []

	#detect input type
	if type(m) is str:
		#resolve menu name
		if m in pagemgr.by_name:
			page = pagemgr.by_name[m]
		elif m in pagemgr.by_modulename:
			page = pagemgr.by_modulename[m]
		menu = page.tree.getroot()
	elif type(m) is ElementTree.Element:
		page = parentpage
		menu = m
	
	for child in menu:
		if child.tag == "script":
			element = {"type": "script"}
			if child.attrib.get("type") == "python":
				#include script
				if "src" in child.attrib:
					try:
						if page.location.joinpath(child.attrib.get("src")).is_file():
							filepath = page.location.joinpath(child.attrib.get("src"))
						else:
							filepath = pagedir.joinpath(child.attrib.get("src"))
						with open(filepath) as f:
							element.update({"script": compile(f.read(), filepath, "exec")})
						res.append(element)
					except Exception as e:
						print("Script include error.")
						print(type(e).__name__ + " " + str(e))
				else:
					element = {"type": "script", "script": child.text}
					res.append(element)
		elif child.tag == "sw.library.list":
			#build library display
			for game in library:
				element = {"type": "sw.game", "display": game.get("name"), "game": game}
				res.append(element)
		elif child.tag == "external":
			#include external element
			mod = child.attrib.get("module")
			if pagemgr.by_modulename.get(mod) is not None:
				res.extend(build_menu_array(mod, page))
			else:
				res.append({"type": "sw.element.error", "display": "This element could not be loaded."})
		else:
			#recursively get child elements
			if child.text and not child.text.isspace():
				element = {"type": child.tag, "display": child.text}
				element.update(child.attrib)
				res.append(element)
			child_elements = build_menu_array(child, page)
			if not len(child_elements) == 0:
				res.extend(child_elements)
			if child.tail and not child.tail.isspace():
				element = {"type": "sw.element.tail", "display": child.tail}
				element.update(child.attrib)
				res.append(element)
	
	return res

def execute_menu(m: list[dict]):
	global current_menu, pagestd
	choices: list[dict] = []
	finaldisplay: list[str] = []
	menu: list[dict] = m.copy()

	choicetypes = [
		"link", "a", #link to another page
		"button", #actionable button
		"exit", #exit
		"restart", #restart
		"sw.game", #game element
		"sw.game.patch", #run patcher for game
		"sw.game.run", #run game
		"sw.game.remove", #delete game
		"sw.library.rebuild", #rebuild library
		"sw.setup.enter_username", #enter uname
		"sw.game.dump", #dump game
		"sw.game.install", #install game
		"sw.sbe.exp.toggle", #toggle sbe exp mode
		"sw.update.prep" #install update
	]
	
	script_context_globals = {"__builtins__": builtins}

	def get_page():
		return get_page_ref().copy()
	
	def get_page_ref():
		build_menu_display()
		return menu
	
	def navigate(m: str | list[dict]):
		if type(m) is str:
			menu = build_menu_array(m)
		elif type(m) is list:
			menu = m
		build_menu_display(menu)

	def cfg_write(section: str, key: str, value):
		global cfg
		if not cfg.has_section(section):
			cfg.add_section(section)

		cfg.set(section, key, value)
		save_config()

	def cfg_read(section: str, key: str):
		global cfg
		try:
			return cfg.get(section, key, fallback=None)
		except:
			return None
		
	def cfg_readint(section: str, key: str):
		global cfg
		try:
			return cfg.getint(section, key, fallback=None)
		except:
			return None
		
	def cfg_readfloat(section: str, key: str):
		global cfg
		try:
			return cfg.getfloat(section, key, fallback=None)
		except:
			return None
		
	def cfg_readbool(section: str, key: str):
		global cfg
		try:
			return cfg.getboolean(section, key, fallback=None)
		except:
			return None

	def build_menu_display(m: list[dict] = None):
		choices.clear()
		finaldisplay.clear()
		if m:
			mm = m
		else:
			mm = menu
		compiled = []
		for item in mm:
			item_type = item.get("type")
			if item_type == "script" and not item.get("executed", False):
				try:
					if item.get("script") not in compiled:
						exec(item.get("script"), script_context_globals)
				except Exception as e:
					print("Script compile error.")
					print(type(e).__name__ + " " + str(e))
				else:
					compiled.append(item.get("script"))
				finally:
					item.update({"executed": True})
			elif item_type in choicetypes:
				choices.append(item)
				finaldisplay.append(f'[{len(choices)}]: {item.get("display", "<undef>")}')
			else:
				display = item.get("display", "")
				if display:
					finaldisplay.append(display)
	
	script_context_globals = {"__builtins__": builtins}
	internalstd = {
		"swpage" : {
			"build_display": build_menu_display,
			"get_page": get_page,
			"get_page_ref": get_page_ref,
			"navigate": navigate,
		},
		"native": {
			"build_menus": load_menus,
			"rebuild_library": build_library
		},
		"cfg": {
			"write": cfg_write,
			"read": cfg_read,
			"readbool": cfg_readbool,
			"readfloat": cfg_readfloat,
			"readint": cfg_readint
		}
	}

	script_context_globals.update({"__builtins__": builtins})
	pagestdmod.import_internals(internalstd)
	#script_context_globals.update({"swinternal": internalstd})
	
	build_menu_display()

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

			if "beforeclick" in choice:
				try:
					exec(choice.get("beforeclick"), script_context_globals)
				except Exception as e:
					print("Script runtime error.")
					print(type(e).__name__ + " " + str(e))

			if choice_type == "link":
				result = choice.get("target", "")
			elif choice_type == "a":
				result = choice.get("href", "")
			elif choice_type == "exit":
				quit()
				sys.exit(0)
			elif choice_type == "restart":
				restart()
				sys.exit(0)
			elif choice_type == "sw.update.prep":
				updpath = pathlib.Path(input("Paste the path of your snakeware update: "))
				try:
					if LAUNCHER_TYPE == "fastboot":
						print("Checking update...")
						if updpath.is_file() and updpath.suffix == ".swupd":
							if zipfile.is_zipfile(updpath):
								with zipfile.ZipFile(updpath, "r") as upd:
									print("Installing update...\nDO NOT CLOSE/INTERUPT")
									upd.extractall(maindir)
							elif tarfile.is_tarfile(updpath):
								with zipfile.ZipFile(updpath, "r") as upd:
									print("Installing update...\nDO NOT CLOSE/INTERUPT)")
									upd.extractall(maindir, filter="data")
							else:
								print("file provided is not an update")
							print("Installing bootfile(s)...\nDO NOT CLOSE/INTERUPT)")
							for dir in maindir.iterdir():
								if dir.endswith(".fastboot"):
									run_fastboot_command(["-Io", maindir.joinpath(dir)])
							os.remove(updpath)
						else:
							print("file provided is not an update")
					elif LAUNCHER_TYPE == "legacy":
						shutil.copy(updpath, maindir)
					else:
						print("Your launcher/launch method does not support updates.")
				except:
					print("an error occured updating")
				else:
					restart()
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
				updpath = pathlib.Path(input("Paste the path of your swPKG archive: ")) 
				if updpath.is_file() and tarfile.is_tarfile(updpath):
					print("Installing...")
					with tarfile.open(updpath, "r:gz") as pkg:
						pkg.extractall(librarydir, filter="data")
					print("Installed.")
					build_library()
				elif updpath.is_file() and zipfile.is_zipfile(updpath):
					print("Installing...")
					with zipfile.ZipFile(updpath, "r") as pkg:
						pkg.extractall(librarydir)
					print("Installed.")
					build_library()
				else:
					print("error, not good path")
			elif choice_type == "sw.game.dump":
				dump_game_zip(choice.get("origin", []), choice.get("game"))
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
				build_library()
				result = "library"

			if "onclick" in choice:
				try:
					exec(choice.get("onclick"), script_context_globals)
				except Exception as e:
					print("Script runtime error.")
					print(type(e).__name__ + " " + str(e))

			if result:
				return result
	else:
		print("\n".join(finaldisplay))
		
#get config
cfg: configparser.ConfigParser = configparser.ConfigParser()
cfg.read(cfgfile)

#get username for session
username = "Guest"
try:
	username = cfg.get("user", "name")
	generate_steam_settings()
	print("Welcome " + username + "!")
except:
	pass

print("Loading...")

compile_pagestd()

#load useful things
try:
	load_library()
except:
	build_library()

get_sbefiles()
load_menus()

try:
	current_menu = None
	if not cfg.getboolean("user", "setup-done", fallback=False):
		current_menu = build_menu_array("oobe\\firstrun")
	else:
		current_menu = build_menu_array("home")

	while True:
		menu_result = execute_menu(current_menu)
		if type(menu_result) is str:
			current_menu = build_menu_array(menu_result)
		elif type(menu_result) is list:
			current_menu = menu_result
except KeyboardInterrupt:
	quit()
	raise
except Exception as e:
	print("A fatal error has occured, and Snakeware has stopped.")
	print("Error code: " + type(e).__name__)
	print(e)
	res = input("[R]estart or [S]hutdown? > ").lower()
	if res == "raise":
		raise
	elif res.startswith("r"):
		restart()
	else:
		quit()
