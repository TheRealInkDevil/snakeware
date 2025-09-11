#core imports
import sys, os, subprocess, threading
import filecmp, shutil, tarfile, zipfile, pathlib
import json, configparser, random, types
import importlib, importlib.util

from xml.etree import ElementTree
#define core directory
maindir: pathlib.Path = pathlib.Path(__file__).parent
if __name__ == "__main__":
	os.chdir(maindir)
sys.path.append(str(maindir))

#critical imports
import swpage3, swapp

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

#library and pages/menus (OBSOLETE)
librarydir: pathlib.Path = maindir.joinpath("library")
#library_meta = {}
#library: list[dict] = []
#launch_option = "quit"

LAUNCHER_NAME = "<none>"
LAUNCHER_TYPE = "self"
LAUNCHER_VER = "<none>"

subprocs: list[dict] = []

os.makedirs(librarydir, exist_ok=True)
os.makedirs(steamsettingsdir, exist_ok=True)

class SwResult:
	def __init__(self, success: bool, result_code: str, return_value = None, exception: Exception = None):
		self.success = success or False
		self.result_code = result_code
		self.return_value = return_value
		self.exception = exception
	
	def __bool__(self):
		return self.success

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

def reg_subproc(proc: subprocess.Popen, name: str, type: str):
	def wait_for_subproc(p: dict):
		pr = p.get("proc")
		pr.wait()
		subprocs.remove(p)

	newproc = {"proc": proc, "name": name, "type": type}
	subprocs.append(newproc)
	threading.Thread(target=wait_for_subproc,args=[newproc], daemon=True).start()

def stop_subprocs(no_escape: bool = True, force: bool = False):
	exit_procs = True
	if not force:
		if len(subprocs) > 0:
			if no_escape:
				print("Some processes are still running!\nTo minimize data loss and lingering processes, please exit the processes before force quitting.")
				input("Press enter to force quit processes > ")
				exit_procs = True
			else:
				print("Some processes are still running!\nTo minimize data loss and lingering processes, please exit the processes before force quitting.\nWould you like to force quit anyway? (y/N)")
				exit_procs = input().lower().startswith("y")
		else:
			return True
	else:
		exit_procs = True
	if exit_procs:
		for proc in subprocs.copy():
			print(f"Trying to kill {proc.get('name')}...\n(if it lingers you will have to kill it yourself!)")
			proc.get("proc").kill()
	return exit_procs

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

#Library Functions ported from Snakeware APIs 1.0.0

library_meta = {}

def get_library() -> list:
	return library_meta.get("library", [])

def get_library_meta() -> list:
	return library_meta

def build_library(librarydir: pathlib.Path) -> None:
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

#gen settings for games
def generate_steam_settings() -> None:
	global cfg, steamsettings, username
	user = configparser.ConfigParser()
	if steamsettings.get("config.user").is_file():
		user.read(steamsettings.get("config.user"))
	if not user.has_section("user::general"):
		user.add_section("user::general")
	user.set("user::general", "account_name", username)
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

def run_game(exec: list, origin: str, name: str):
	print("Preparing " + name + "...")
	patch_game(origin)
	generate_steam_settings()
	print(f"Running {name}... (if it doesn't work, run the patcher!)")
	with open(pathlib.Path(origin, "stdout.log"), "w") as stdoutfile:
		reg_subproc(subprocess.Popen(exec, cwd=origin, stdout=stdoutfile, shell=True), name, "game")

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
	if username:
		cfg.set("user", "name", username)
	with open(cfgfile, "w") as cfgtmp:
		cfg.write(cfgtmp)

SWAPP_SDK_CURRENT_VERSION = 1

def load_swapp(app_path: pathlib.Path):
	manifest = ElementTree.parse(app_path.joinpath("manifest.xml")).getroot()
	app = swapp.App(app_path)
	ident = manifest.find("Identity")
	targetsdk = int(manifest.attrib.get("version", 0))
	if not targetsdk:
		return SwResult(False, "app_targetsdk_missing")
		
	minsdk = int(manifest.attrib.get("min", 0)) or targetsdk
	if minsdk > SWAPP_SDK_CURRENT_VERSION:
		return SwResult(False, "app_unsupported_sdk")
	
	maxsdk = int(manifest.attrib.get("max", 0))
	if SWAPP_SDK_CURRENT_VERSION > maxsdk and maxsdk > 0:
		return SwResult(False, "app_sdk_too_new")
	if ident is None:
		return SwResult(False, "app_identity_missing")
	app.name = ident.findtext("Name", None)
	if app.name is None:
		return SwResult(False, "app_missing_name")
	app.version = ident.findtext("Version", None)
	if app.name is None:
		return SwResult(False, "app_missing_version")
	app.display_name = ident.findtext("DisplayName", app.name)
	app.desc = ident.findtext("Desc", "")

	appnames = [app.name]

	deps = manifest.find("Depends")
	if deps is not None:
		for entry in deps:
			if entry.tag == "App":
				if not entry.attrib.get("appid") in installed_apps:
					return SwResult(False, "app_appdepend_missing", entry.attrib.get("appid"))
			elif entry.tag == "Module":
				if not entry.attrib.get("modid") in sys.modules:
					return SwResult(False, "app_moddepend_missing", entry.attrib.get("modid"))
	
	provides = manifest.find("Provides")
	if provides is not None:
		for entry in provides:
			if entry.tag == "App":
				if not entry.attrib.get("appid") in installed_apps:
					app.provides.append(entry.attrib.get("appid"))
					if not entry.attrib.get("nocompile"):
						appnames.append(entry.attrib.get("appid"))

	swpage3.element_registry.create_scope(app.name)
	swpage3.element_registry.push_scope(app.name)
	code = manifest.find("Modules")
	if code is not None:
		def split_module_path(path: str) -> list[str]:
			parts = path.split(".")
			result = []
			for i in range(1, len(parts) + 1):
				slice_parts = parts[:i]
				module_path = ".".join(slice_parts)
				result.append(module_path)
			return result
		def attach_child_modules(module_path: str):
			if module_path not in sys.modules:
				return
			
			module = sys.modules[module_path]
			if '.' not in module_path:
				return
			parent_path, child_name = module_path.rsplit('.', 1)
			attach_child_modules(parent_path)
			setattr(module, child_name, module)
		
		fail = None
		path_to_clean = []
		mod_to_clean = []
		mods_to_dummy = []
		try:
			for mod in code:
				if mod.tag == "Module" and "path" in mod.attrib:
					full_mod_pth = app_path / mod.attrib.get("path")
					mod_pth = full_mod_pth.relative_to(app_path).with_suffix("")
					if not full_mod_pth.exists():
						print(f"WARNING (for {app.name}): {mod_pth} is not exist.")
						continue
					
					for appname in appnames:
						mod_name = None
						if "name" in mod.attrib:
							if mod.attrib.get("name").strip() or mod.attrib.get("name") == "__init__":
								mod_name = f"{appname}"
							else:
								mod_name = f"{appname}.{mod.attrib.get("name")}"
						else:
							if mod_pth.stem == "__init__":
								if mod_pth.parent.as_posix() == ".":
									mod_name = f"{appname}"
								else:
									mod_name = f"{appname}.{mod_pth.parent.as_posix().replace("/", ".")}"
							else:
								mod_name = f"{appname}.{mod_pth.as_posix().replace("/", ".")}"
						to_dumb = split_module_path(mod_name)
						for dumb in to_dumb:
							if dumb not in mods_to_dummy:
								mods_to_dummy.append(dumb)

						mod_to_clean.append(mod_name)
						sys.path.append(full_mod_pth)
						path_to_clean.append(full_mod_pth)
						spec = importlib.util.spec_from_file_location(mod_name, full_mod_pth)
						module = importlib.util.module_from_spec(spec)
						module.__path__ = []
						sys.modules[mod_name] = module
						spec.loader.exec_module(module)
						app.modules.update({mod_name: module})
		except Exception as e:
			fail = e
		else:
			mod_to_clean.clear()
			for modd in mods_to_dummy:
				if modd not in sys.modules:
					dumb_mod = types.ModuleType(modd)
					sys.modules[modd] = dumb_mod
			for modd in mods_to_dummy:
				attach_child_modules(modd)
		finally:
			for mod in mod_to_clean:
				sys.modules.pop(mod, None)
			for pth in path_to_clean:
				try:
					sys.path.remove(pth)
				except:
					pass
			if fail:
				return SwResult(False, "app_module_import_exception", None, fail)
	entrypoints = manifest.find("Entrypoints")
	if entrypoints is not None:
		for entry in entrypoints:
			if entry.tag == "PageEntry":
				page_path = app_path.joinpath(entry.attrib.get("path"))
				app.entrypoints.update({entry.attrib.get("id"): ElementTree.parse(page_path).getroot()})
	page_inc = manifest.find("PageIncludes")
	if page_inc is not None:
		for entry in page_inc:
			if entry.tag == "Include":
				app.page_includes.append(entry.attrib.get("appid"))
	swpage3.element_registry.pop_scope()
	return SwResult(True, "app_loaded", app)

installed_apps: swapp.AppDB = swapp.AppDB()

def load_swapps() -> None:
	pth = appdir
	installed_apps.apps.clear()
	installed_apps.provided.clear()
	retry = {}
	next_retry = {}
	for app_path in pth.iterdir():
		if app_path.is_dir() and app_path.joinpath("manifest.xml").exists():
			retry.update({app_path: 0})
	while len(retry) > 0:
		for retry_pth in retry:
			result = load_swapp(retry_pth)
			if result:
				app: swapp.App = result.return_value
				app.db = installed_apps
				installed_apps.add_app(app)
			else:
				if retry[retry_pth] > 1000:
					print(f"Failed to load app from {retry_pth}")
					continue
				next_retry.update({retry_pth: retry[retry_pth] + 1})
		retry = next_retry.copy()
		next_retry.clear()

def process_handler_calls(capp: swapp.PageHandler):
	if "_sw_page_handler_calls" in capp.cdata:
		for call in capp.cdata.get("_sw_page_handler_calls"):
			func, *args = call
			appdat: swapp.App = capp.app_data
			match func:
				case "switch_page":
					capp.push_page(ElementTree.parse(appdat.origin.joinpath(args[0])).getroot(), args=args[1:])
				case "replace_page":
					capp.replace_page(ElementTree.parse(appdat.origin.joinpath(args[0])).getroot(), args=args[1:])
				case "switch_app":
					app = installed_apps.get_app(args[0])
					if not app:
						raise Exception(f"E: App {args[0]} not installed.")
					app_handler.push_app(app, "main" if len(args) < 2 else args[1], None if len(args) < 3 else args[2], None if len(args) < 4 else args[3])
				case "replace_app":
					app = installed_apps.get_app(args[0])
					if not app:
						raise Exception(f"E: App {args[0]} not installed.")
					app_handler.replace_app(app, "main" if len(args) < 2 else args[1], None if len(args) < 3 else args[2], None if len(args) < 4 else args[3])
				case "run_game":
					id_to_launch = args[0]
					for game in get_library():
						if game.get("id") == id_to_launch:
							if game.get("exec"):
								run_game(game.get("exec"), game.get("origin"), game.get("name", game.get("id")))
								break
				case "patch_game":
					id_to_launch = args[0]
					for game in get_library():
						if game.get("id") == id_to_launch:
							patch_game(game.get("origin"), False)
							break
				case "reload_apps":
					load_swapps()
				case "sw_restart":
					restart()
				case "sw_quit":
					quit()
				case _:
					print(f"Unknown SWCALL: {func}")
		capp.cdata.pop("_sw_page_handler_calls")

def get_userdata(src: pathlib.Path):
	try:
		from snakeware.apis.user import SwUser
		with SwUser(userfile) as udat:
			userdata = udat.getall()
			return userdata
	except ImportError:
		print("E: Snakeware User API not installed!")
		return {}
	except:
		print("E: Snakeware failed to get user data!")
		return {}

def save_userdata(src: pathlib.Path, userdat: dict):
	try:
		from snakeware.apis.user import SwUser
		with SwUser(userfile) as udat:
			userdata = udat.getall()
	except ImportError:
		print("E: Snakeware User API not installed!")
	except:
		print("E: Snakeware failed to save user data!")

if __name__ == "__main__":
	print("Starting Snakeware 3.0...")
	LAUNCHER_TYPE, LAUNCHER_NAME, LAUNCHER_VER = detect_launcher()
	if LAUNCHER_TYPE != "self":
		print(f"Running with {LAUNCHER_NAME}v{LAUNCHER_VER} ({LAUNCHER_TYPE})")

	#get config
	cfg: configparser.ConfigParser = configparser.ConfigParser()
	cfg.read(cfgfile)

	get_sbefiles()
	load_swapps()

	udatready = False

	userdata = get_userdata(userfile)

	#get username for session
	username = userdata.get("name")

	try:
		from snakeware.apis.library import *
		load_library(librarydir)
		library = get_library()
		if len(library) < 1:
			build_library(librarydir)
	except ImportError:
		print("Library APIs Unavalible!")

	try:
		boot_app_name = cfg.get("sys", "boot-app", fallback="boot2")
		if not boot_app_name:
			raise Exception("Boot App not defined!")
		app_ctx_vars = {
			"sw_username": username,
		}
		app_handler = swapp.AppHandler()
		app_handler.cdata.update({
			"sw_maindir": maindir,
			"sw_librarydir": librarydir,
		})
		boot_app = installed_apps.get_app(boot_app_name)
		if not boot_app:
			raise Exception("Boot App not installed!")
		app_handler.push_app(boot_app, context_vars=app_ctx_vars)
		
		while True:
			current_app = app_handler.current_app
			if current_app is None:
				quit()
				raise Exception("Somehow persisted past quit().")
			if current_app.current_page is None:
				app_handler.pop_app()
				continue
			page_context = swpage3.PageContext(current_app, app_handler, current_app.app_data)
			page_context.app_data = current_app.cdata
			page_context.global_data = app_handler.cdata
			current_app.cdata.update({"_ctx_vars": app_ctx_vars})
			#print("\033c", end="")
			try:
				rendered_page = swpage3.get_renderable(current_app.current_page.render(page_context)).render(page_context)
				if rendered_page:
					print(rendered_page)
				process_handler_calls(current_app)
				if len(page_context._handlers) > 0:
					handler_to_call = None
					while not handler_to_call:
						try:
							handler_to_call = int(input("> "))
						except ValueError:
							print("Invalid entry, try again.")
						else:
							h = page_context.get_handler(handler_to_call)
							if h:
								h()
					process_handler_calls(current_app)
			except Exception as e:
				#handle app crash
				failedapp = app_handler.current_app.app_data
				app_handler.pop_app()
				if not app_handler.current_app:
					raise
				print(f"An uncaught error has occured in the following app: {failedapp.display_name} ({failedapp.name})")
				print("Error code: " + type(e).__name__)
				print(e)
	except KeyboardInterrupt:
		print("Interrupted.")
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