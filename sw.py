#core imports
import sys, os, subprocess, threading
import pathlib, shutil, tarfile
import json, types, tomllib
import importlib, importlib.util, inspect

from xml.etree import ElementTree
#define core directory and system config file
maindir: pathlib.Path = pathlib.Path(__file__).parent
systemconfigfile: pathlib.Path = maindir.joinpath("sw.cfg")
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
apppermsfile: pathlib.Path = maindir.joinpath("app_permissions.priv")
apppermsdetailsfile: pathlib.Path = maindir.joinpath("app_permission_details.json")

system_config: dict = {}
installed_apps: swapp.AppDB = swapp.AppDB()
app_perms: dict = {}
app_perm_details: dict = {}

SWAPP_SDK_CURRENT_VERSION = 1

class SwResult:
	def __init__(self, success: bool, result_code: str, return_value = None, exception: Exception = None):
		self.success = success or False
		self.result_code = result_code
		self.return_value = return_value
		self.exception = exception
	
	def __bool__(self):
		return self.success

def quit():
	sys.exit(0)

#convert to number
def number_input(ask: str) -> int:
	while True:
		try:
			return int(input(ask))
		except ValueError:
			print("that's not a number, try again.")

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
	
	permissions = manifest.find("Permissions")
	if permissions is not None:
		for entry in permissions:
			if entry.tag == "Install":
				app.permissions.setdefault("install", []).append(entry.attrib.get("permission"))
			elif entry.tag == "Request":
				app.permissions.setdefault("request", []).append(entry.attrib.get("permission"))

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

def install_swapp(archive_path: pathlib.Path, interactive: bool = True, accept_perms: bool = False):
	if not archive_path.is_file():
		raise FileNotFoundError("Archive Path not exist.")
	try:
		with tarfile.open(archive_path, "r:xz") as archive:
			try:
				manifestinfo = archive.getmember("manifest.xml")
				data = archive.extractfile(manifestinfo)
				manifest = ElementTree.parse(data).getroot()
				appidentity = manifest.find("Identity")
				appname = appidentity.findtext("Name")
				appdname = appidentity.findtext("DisplayName")
				appver = appidentity.findtext("Version")
				apppermselement = manifest.find("Permissions")
				appperms = []
				if apppermselement is not None:
					appperms = [p.attrib.get("permission") for p in apppermselement if p.tag == "Install"]
				installpath = appdir / appname
				prev_version = installed_apps.get_app(appname)
				if interactive:
					print(f"Install {appdname}? ({appname})")
					if len(appperms) > 0:
						print("It requires the following permissions:")
						for perm in appperms:
							details = app_perm_details.get(perm)
							if details:
								print(details.get("display-name", perm))
							else:
								print(perm)
					installcheck = input("Install? [y/N] > ")
					if not installcheck.lower().startswith("y"):
						return SwResult(False, "user_canceled")
				if prev_version and installpath.exists():
					if appver < prev_version.version:
						return SwResult(False, "outdated_version")
					shutil.rmtree(installpath)
				archive.extractall(installpath, filter="tar")
				load = load_swapp(installpath)
				if load:
					installed = load.return_value
					installed.db = installed_apps
					installed_apps.update_app(installed)
					if interactive:
						app_perms.setdefault(appname, []).extend(appperms)
						save_app_perms()
					elif accept_perms:
						app_perms.setdefault(appname, []).extend(appperms)
						save_app_perms()
					return SwResult(True, "installed")
				else:
					return SwResult(False, "load_failed")
			except KeyError:
				return SwResult(False, "manifest_missing")
	except tarfile.ReadError:
		return SwResult(False, "read_fail")
	except tarfile.CompressionError:
		return SwResult(False, "compress_fail")
	

def init_swapp(app_meta: swapp.AppMetadata, entrypoint_id: str, passed_args: list | None = None):
	args = passed_args.copy() if passed_args else []
	entrypoint = app_meta.entrypoints.get(entrypoint_id)
	if not entrypoint:
		raise Exception(f"Entrypoint {entrypoint_id} Not Found for app {app_meta.name}")
	match entrypoint.entry_type:
		case swapp.AppEntrypoint.CLASS_ENTRY:
			app: swapp.App = entrypoint.data(entrypoint_id, *args)
			running_app: swapp.RunningApp = swapp.RunningApp(app, app_meta)
			return running_app
		case swapp.AppEntrypoint.FUNC_ENTRY:
			raise Exception("FUNC_ENTRY is not implemented currently")
		case swapp.AppEntrypoint.PAGE_ENTRY:
			raise Exception("PAGE_ENTRY is not implemented currently")

def call_swapp_event(running_app: swapp.RunningApp, app_stack: swapp.AppStack, event_id: int, event_data: dict = None):
	event_data = event_data if event_data else {}
	app_event: swapp.AppEvent = swapp.AppEvent(event_id, event_data)
	def handle_generator(generator):
		for signal in generator:
			if inspect.isgeneratorfunction(signal):
				handle_generator(signal())
			elif inspect.isgenerator(signal):
				handle_generator(signal)
			elif type(signal) is swapp.signals.AppSignal:
				sig_result = handle_swapp_signal(running_app, app_stack, signal, False)
				if not sig_result:
					break
	try:
		if inspect.isgeneratorfunction(running_app.app.ev_signal):
			handle_generator(running_app.app.ev_signal(app_event))
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
	perms = app_perms.get(running_app.app_metadata.name, [])
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
			new_app_args = signal.data.get("args", []) if type(signal.data.get("args", [])) is list else []
			new_app_meta = installed_apps.get_app(new_app_name)
			try:
				new_app = init_swapp(new_app_meta, new_app_entry, new_app_args)
				new_app.status = swapp.APPSTATUS_STARTING
				app_stack.add_to_stack(new_app)
				running_app.status = swapp.APPSTATUS_DEACTIVATING
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
			if "fs.storage.app" not in perms:
				signal.success = False
				return True
			data_folder_name = running_app.app_metadata.name
			data_folder = appstoragedir / data_folder_name
			data_folder.mkdir(parents=True, exist_ok=True)
			signal.result.update({"folder": str(data_folder)})
			signal.success = True
			return True
		case swapp.signals.FS_GET_SHAREDSTORAGE:
			if "fs.storage.shared" not in perms:
				signal.success = False
				return True
			data_folder = sharedstoragedir
			data_folder.mkdir(parents=True, exist_ok=True)
			signal.result.update({"folder": str(data_folder)})
			signal.success = True
			return True
		case swapp.signals.PERMISSIONS_TEST:
			perms_to_test = []
			if "perm" in signal.data:
				perms_to_test.append(signal.data.get("perm"))
			if "perms" in signal.data:
				for perm in signal.data.get("perms", []):
					perms_to_test.append(perm)
			for p in perms_to_test:
				if p not in perms:
					signal.success = False
					return True
			signal.success = True
			return True
		case swapp.signals.PERMISSIONS_REQUEST | swapp.signals.PERMISSIONS_REQUEST_INSTALL:
			requested_to_filter = []
			requested_perms = []
			if "perm" in signal.data:
				requested_to_filter.append(signal.data.get("perm"))
			if "perms" in signal.data:
				for perm in signal.data.get("perms", []):
					requested_to_filter.append(perm)
			for filtered in requested_to_filter:
				if filtered not in perms:
					requested_perms.append(filtered)
			allowed_perms = []
			if signal.id == swapp.signals.PERMISSIONS_REQUEST_INSTALL:
				allowed_perms.extend(running_app.app_metadata.permissions.get("install", []))
			if signal.id == swapp.signals.PERMISSIONS_REQUEST:
				allowed_perms.extend(running_app.app_metadata.permissions.get("request", []))
			success = True
			for requested in requested_perms:
				if requested in allowed_perms:
					perm_details = app_perm_details.get(requested)
					if perm_details:
						print(f"{running_app.app_metadata.display_name} ({running_app.app_metadata.name}) is requesting the following permission: {perm_details.get("display-name", requested)}")
						install_check = input("Allow? [y/N] > ").lower()
						if not install_check.startswith("y"):
							success = False
							break
					else:
						print(f"{running_app.app_metadata.display_name} ({running_app.app_metadata.name}) is requesting the following permission: {requested}")
						install_check = input("Allow? [y/N] > ").lower()
						if not install_check.startswith("y"):
							success = False
							break
				else:
					success = False
					break
			if success:
				app_perms.setdefault(running_app.app_metadata.name, []).extend(requested_perms)
				save_app_perms()
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
			signal.success = False
	return True

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

def load_app_perms():
	app_perms.clear()
	if apppermsfile.is_file():
		with open(apppermsfile) as apfile:
			app_perms.update(json.load(apfile))
	if apppermsdetailsfile.is_file():
		app_perm_details.clear()
		with open(apppermsdetailsfile) as apfile:
			app_perm_details.update(json.load(apfile))

def save_app_perms():
	with open(apppermsfile, "w") as apfile:
		json.dump(app_perms, apfile)

def load_system_config(path: pathlib.Path):
	system_config.clear()
	with open(path, "rb") as sysconfig:
		system_config.update(tomllib.load(sysconfig).get("system", {}))

if __name__ == "__main__":
	try:
		print("Starting Snakeware 3.0...")
		print("Loading system config...")
		load_system_config(systemconfigfile)

		print("Running self-test...")

		if system_config.get("verbose", False):
			print("Checking for appdir...")
		if system_config.get("appdir"):
			appdir = pathlib.Path(system_config.get("appdir"))
		if not appdir or not appdir.is_dir():
			raise Exception("Self-test failed.")
		
		if system_config.get("verbose", False):
			print("Checking for storagedir...")
		if system_config.get("storagedir"):
			storagedir = pathlib.Path(system_config.get("storagedir"))
		if not storagedir or not storagedir.is_dir():
			raise Exception("Self-test failed.")
		
		if system_config.get("verbose", False):
			print("Checking for appstoragedir...")
		if system_config.get("appstoragedir"):
			appstoragedir = pathlib.Path(system_config.get("appstoragedir"))
		if not appstoragedir or not appstoragedir.is_dir():
			if system_config.get("verbose", False):
				print("appstoragedir failed...using fallback")
			appstoragedir = storagedir.joinpath("app")
		
		if system_config.get("verbose", False):
			print("Checking for sharedstoragedir...")
		if system_config.get("sharedstoragedir"):
			sharedstoragedir = pathlib.Path(system_config.get("sharedstoragedir"))
		if not sharedstoragedir or not sharedstoragedir.is_dir():
			if system_config.get("verbose", False):
				print("sharedstoragedir failed...using fallback")
			sharedstoragedir = storagedir.joinpath("shared")

		if system_config.get("verbose", False):
			print("Loading apps...")
		load_swapps()
		if system_config.get("verbose", False):
			print("Loading app permissions...")
		load_app_perms()

		boot_app_name = system_config.get("boot-app") if system_config.get("boot-app") else "boot2"
		if system_config.get("verbose", False):
			print(f"Fetching boot app {boot_app_name}...")
		boot_app = installed_apps.get_app(boot_app_name)
		if not boot_app:
			raise Exception(f"Boot App {boot_app_name} not installed!")
	
		if system_config.get("verbose", False):
			print(f"Starting boot app {boot_app_name}...")

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
						app.status = swapp.APPSTATUS_ACTIVATING
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_START)
						active_apps += 1
					case swapp.APPSTATUS_ACTIVATING:
						app.status = swapp.APPSTATUS_ACTIVE
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_ACTIVATING)
						active_apps += 1
					case swapp.APPSTATUS_DEACTIVATING:
						app.status = swapp.APPSTATUS_INACTIVE
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_DEACTIVATING)
						active_apps += 1
					case swapp.APPSTATUS_ACTIVE:
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_PROCESS)
						active_apps += 1
					case swapp.APPSTATUS_INACTIVE:
						call_swapp_event(app, app_stack, swapp.AppEvent.APP_INACTIVE_PROCESS)
					case _:
						to_cleanup.append(app)
			for clean in to_cleanup:
				app_stack.running.remove(clean)
			if active_apps < 1:
				for app in reversed(app_stack.running):
					if app.status == swapp.APPSTATUS_INACTIVE:
						app.status = swapp.APPSTATUS_ACTIVATING
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
