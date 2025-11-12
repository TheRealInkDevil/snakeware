#core imports
import sys, os, subprocess, threading
import filecmp, shutil, tarfile, zipfile, pathlib
import json, configparser, random, types
import importlib, importlib.util, inspect

from xml.etree import ElementTree
#define core directory
maindir: pathlib.Path = pathlib.Path(__file__).parent
if __name__ == "__main__":
	os.chdir(maindir)
sys.path.append(str(maindir))

#critical imports
import swapp, swapp.signals

#define other directories
appdir: pathlib.Path = maindir.joinpath("app")
storagedir: pathlib.Path = maindir.joinpath("storage")
appstoragedir: pathlib.Path = storagedir.joinpath("app")
sharedstoragedir: pathlib.Path = storagedir.joinpath("shared")
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

subprocs: list[dict] = []

class SwResult:
	def __init__(self, success: bool, result_code: str, return_value = None, exception: Exception = None):
		self.success = success or False
		self.result_code = result_code
		self.return_value = return_value
		self.exception = exception
	
	def __bool__(self):
		return self.success

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
	sys.exit(0)

#get file paths for files
def get_sbefiles(experimental: bool = False) -> None:
	if experimental:
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

def get_value_of_path(pypath: str):
	to_dig = pypath.split(".")
	is_top_level = True
	value = None
	for dig in to_dig:
		if is_top_level:
			value = globals().get(dig)
			is_top_level = False
		else:
			value = getattr(value, dig)
	return value
	

def load_swapp(app_path: pathlib.Path):
	manifest = ElementTree.parse(app_path.joinpath("manifest.xml")).getroot()
	app = swapp.AppMetadata(app_path)
	#detect sdk version bounds
	targetsdk = int(manifest.attrib.get("version", 0))
	if not targetsdk:
		return SwResult(False, "app_targetsdk_missing")
	minsdk = int(manifest.attrib.get("min", targetsdk))
	if minsdk > SWAPP_SDK_CURRENT_VERSION:
		return SwResult(False, "app_unsupported_sdk")
	maxsdk = int(manifest.attrib.get("max", 0))
	if SWAPP_SDK_CURRENT_VERSION > maxsdk and maxsdk > 0:
		return SwResult(False, "app_sdk_too_new")
	
	#setup app identity
	ident = manifest.find("Identity")
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
	modnames = []

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
			module_to_attach = sys.modules[module_path]
			try:
				parent_path, child_name = module_path.rsplit('.', 1)
				attach_child_modules(parent_path)
				parent_module = sys.modules[parent_path]
				if not hasattr(parent_module, child_name):
					setattr(parent_module, child_name, module_to_attach)
			except ValueError:
				return
		
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
						globals().update({mod_name: module})
						spec.loader.exec_module(module)
						app.modules.update({mod_name: module})
						modnames.append(mod_name)
		except Exception as e:
			fail = e
		else:
			mod_to_clean.clear()
			for modd in mods_to_dummy:
				if modd not in sys.modules:
					dumb_mod = types.ModuleType(modd)
					sys.modules[modd] = dumb_mod
					globals().update({modd: dumb_mod})
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
			match entry.tag:
				case "ClassEntry":
					class_path = entry.attrib.get("class")
					app.entrypoints.update({entry.attrib.get("id"): swapp.AppEntrypoint(entry.attrib.get("id"), swapp.AppEntrypoint.CLASS_ENTRY, get_value_of_path(class_path))})
				case "FuncEntry":
					func_path = entry.attrib.get("func")
					app.entrypoints.update({entry.attrib.get("id"): swapp.AppEntrypoint(entry.attrib.get("id"), swapp.AppEntrypoint.FUNC_ENTRY, get_value_of_path(func_path))})
				case "PageEntry":
					page_path = app_path.joinpath(entry.attrib.get("path"))
					app.entrypoints.update({entry.attrib.get("id"): swapp.AppEntrypoint(entry.attrib.get("id"), swapp.AppEntrypoint.PAGE_ENTRY, ElementTree.parse(page_path).getroot())})
				
	page_inc = manifest.find("PageIncludes")
	if page_inc is not None:
		for entry in page_inc:
			if entry.tag == "Include":
				app.page_includes.append(entry.attrib.get("appid"))
	return SwResult(True, "app_loaded", app)

def init_swapp(app_meta: swapp.AppMetadata, entrypoint_id: str):
	entrypoint = app_meta.entrypoints.get(entrypoint_id)
	if not entrypoint:
		raise Exception(f"Entrypoint {entrypoint_id} Not Found for app {app_meta.name}")
	match entrypoint.entry_type:
		case swapp.AppEntrypoint.CLASS_ENTRY:
			app: swapp.App = entrypoint.data(entrypoint_id)
			running_app: swapp.RunningApp = swapp.RunningApp(app, app_meta)
			return running_app
		case swapp.AppEntrypoint.FUNC_ENTRY:
			raise Exception("FUNC_ENTRY is not implemented currently")
		case swapp.AppEntrypoint.PAGE_ENTRY:
			raise Exception("PAGE_ENTRY is not implemented currently")

def call_swapp_event(running_app: swapp.RunningApp, app_stack: swapp.AppStack, event_id: int, event_data: dict = None):
	event_data = event_data if event_data else {}
	app_event: swapp.AppEvent = swapp.AppEvent(event_id, event_data)
	try:
		if inspect.isgeneratorfunction(running_app.app.ev_signal):
			for signal in running_app.app.ev_signal(app_event):
				if type(signal) is swapp.signals.AppSignal:
					sig_result = handle_swapp_signal(running_app, app_stack, signal, False)
					if not sig_result:
						break
		else:
			signal = running_app.app.ev_signal(app_event)
			if type(signal) is swapp.signals.AppSignal:
				handle_swapp_signal(running_app, app_stack, signal, False)
	except swapp.signals.AppSignal as raised_signal:
		handle_swapp_signal(running_app, app_stack, raised_signal, True)
	except Exception as e:
		running_app.status = swapp.APPSTATUS_NONE
		print(f"Unfortunately, {running_app.app_metadata.display_name} has stopped.\n" +
		f"Error code: {type(e).__name__}\n" +
		f"{str(e)}")
		input("Press return to exit > ")

def handle_swapp_signal(running_app: swapp.RunningApp, app_stack: swapp.AppStack, signal: swapp.signals.AppSignal, is_interupt: bool):
	match signal.id:
		case swapp.signals.EXIT_SUCCESS:
			running_app.status = swapp.APPSTATUS_EXITED_SUCCESS
			signal.success = True
			return False
		case swapp.signals.EXIT_FAILURE:
			running_app.status = swapp.APPSTATUS_EXITED_FAILURE
			signal.success = True
			return False
		case swapp.signals.APP_OPEN:
			new_app_name = signal.data.get("target")
			new_app_entry = signal.data.get("entry", "main")
			new_app_meta = installed_apps.get_app(new_app_name)
			try:
				new_app = init_swapp(new_app_meta, new_app_entry)
				new_app.status = swapp.APPSTATUS_STARTING
				app_stack.add_to_stack(new_app)
				running_app.status = swapp.APPSTATUS_ENTERING_BACKGROUND
				signal.success = True
				return False
			except:
				signal.success = False
		case swapp.signals.APP_REPLACE:
			new_app_name = signal.data.get("target")
			new_app_entry = signal.data.get("entry", "main")
			new_app_meta = installed_apps.get_app(new_app_name)
			try:
				new_app = init_swapp(new_app_meta, new_app_entry)
				new_app.status = swapp.APPSTATUS_STARTING
				app_stack.add_to_stack(new_app)
				running_app.status = swapp.APPSTATUS_NONE
				signal.success = True
				return False
			except:
				signal.success = False
		case swapp.signals.FS_GET_APPSTORAGE:
			data_folder_name = running_app.app_metadata.name
			data_folder = appstoragedir / data_folder_name
			data_folder.mkdir(parents=True, exist_ok=True)
			signal.result.update({"folder": str(data_folder)})
			signal.success = True
			return True
		case swapp.signals.FS_GET_SHAREDSTORAGE:
			data_folder = sharedstoragedir
			data_folder.mkdir(parents=True, exist_ok=True)
			signal.result.update({"folder": str(data_folder)})
			signal.success = True
			return True
		case swapp.signals.APPDB_QUERY:
			results = []
			query_type = signal.data.get("type", "all")
			query_name = signal.data.get("name")

			if query_type == "all":
				for app_name in installed_apps.apps:
					app_meta = installed_apps.get_app(app_name, True)
					if app_meta:
						results.append({
							"name": app_meta.name,
							"dname": app_meta.display_name,
							"desc": app_meta.desc,
							"ver": app_meta.version,
							"provides": app_meta.provides.copy(),
							"entries": list(app_meta.entrypoints.keys())
						})
				signal.result.update({"apps": results})
				signal.success = True
				return True

			if not query_name:
				signal.success = False
				return True
			
			match query_type:
				case "any":
					app_meta = installed_apps.get_app(app_name)
					if app_meta:
						result = {
							"name": app_meta.name,
							"dname": app_meta.display_name,
							"desc": app_meta.desc,
							"ver": app_meta.version,
							"provides": app_meta.provides.copy(),
							"entries": list(app_meta.entrypoints.keys())
						}
						signal.result.update({"app": result})
						signal.success = True
						return True
					else:
						signal.success = False
						return True
				case "exact":
					app_meta = installed_apps.get_app(app_name, True)
					if app_meta:
						result = {
							"name": app_meta.name,
							"dname": app_meta.display_name,
							"desc": app_meta.desc,
							"ver": app_meta.version,
							"provides": app_meta.provides.copy(),
							"entries": list(app_meta.entrypoints.keys())
						}
						signal.result.update({"app": result})
						signal.success = True
						return True
					else:
						signal.success = False
						return True

				case _:
					signal.success = False
					return True

		case _:
			print(f"[!] snakeware: Unhandled Signal {signal.id} from {running_app.app_metadata.name}")
	return True

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
				app: swapp.AppMetadata = result.return_value
				app.db = installed_apps
				installed_apps.add_app(app)
			else:
				if retry[retry_pth] > 5:
					print(f"Failed to load app from {retry_pth}")
					print(result.exception)
					continue
				next_retry.update({retry_pth: retry[retry_pth] + 1})
		retry = next_retry.copy()
		next_retry.clear()

if __name__ == "__main__":
	print("Starting Snakeware 3.0...")

	#get config
	cfg: configparser.ConfigParser = configparser.ConfigParser()
	cfg.read(cfgfile)

	get_sbefiles()
	load_swapps()

	try:
		boot_app_name = cfg.get("sys", "boot-app", fallback="boot2")
		if not boot_app_name:
			raise Exception("Boot App not defined!")
		boot_app = installed_apps.get_app(boot_app_name)
		if not boot_app:
			raise Exception(f"Boot App {boot_app_name} not installed!")
	
		app_stack: swapp.AppStack = swapp.AppStack()
		boot_run = init_swapp(boot_app, "boot")
		boot_run.status = swapp.APPSTATUS_BOOTING
		app_stack.add_to_stack(boot_run)
		while len(app_stack.running):
			to_cleanup = []
			active_apps = 0
			for app in app_stack.running.copy():
				match app.status:
					case swapp.APPSTATUS_BOOTING:
						app.status = swapp.APPSTATUS_NONE
						call_swapp_event(app, app_stack, swapp.AppEvent.SNAKEWARE_BOOTUP)
						active_apps += 1
					case swapp.APPSTATUS_STARTING:
						app.status = swapp.APPSTATUS_ENTERING_FOREGROUND
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_STARTING)
						active_apps += 1
					case swapp.APPSTATUS_ENTERING_FOREGROUND:
						app.status = swapp.APPSTATUS_FOREGROUND
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_ENTERING_FOREGROUND)
						active_apps += 1
					case swapp.APPSTATUS_ENTERING_BACKGROUND:
						app.status = swapp.APPSTATUS_BACKGROUND
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_ENTERING_BACKGROUND)
						active_apps += 1
					case swapp.APPSTATUS_FOREGROUND:
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_FRAME)
						active_apps += 1
					case swapp.APPSTATUS_BACKGROUND:
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_FRAME_BACKGROUND)
					case _:
						to_cleanup.append(app)
			for clean in to_cleanup:
				app_stack.running.remove(clean)
			if active_apps < 1:
				for app in reversed(app_stack.running):
					if app.status == swapp.APPSTATUS_BACKGROUND:
						app.status = swapp.APPSTATUS_ENTERING_FOREGROUND
						break


	except KeyboardInterrupt:
		print("Interrupted.")
		quit()
		raise
	except Exception as e:
		print("A fatal error has occured, and Snakeware has stopped.")
		print("Error code: " + type(e).__name__)
		print(e)
		res = input("Press return to shutdown > ").lower()
		if res == "raise":
			raise
		else:
			quit()
