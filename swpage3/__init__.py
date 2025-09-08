from xml.etree.ElementTree import Element, fromstring
from ._internal import ElementRegistry
import re

element_registry: ElementRegistry = ElementRegistry()

class PageXML:
    def __init__(self, txt):
        self.txt = txt
    
    def __str__(self):
        return self.txt

class PageContext:
    def __init__(self, page_hander=None, app_handler=None, app=None):
        self._handlers: list = []
        self._event_listeners: dict[str, list] = {}
        self._ctxevent_listeners: dict[str, list] = {}
        self._counter = 1
        self.global_data = {}
        self.app_data = {}
        self.page_handler = page_hander
        self.app_handler = app_handler
        self.app = app
    
    def register(self, handler):
        idx = self._counter
        self._handlers.append(handler)
        self._counter += 1
        return idx
    
    def listen_for_event(self, event, callback):
        self._event_listeners.setdefault(event, [])
        self._event_listeners[event].append(callback)
    
    def listen_for_ctxevent(self, event, callback):
        self._ctxevent_listeners.setdefault(event, [])
        self._ctxevent_listeners[event].append(callback)
    
    def raise_event(self, event, args=None, kwargs=None):
        if event in self._event_listeners:
            for e in self._event_listeners[event]:
                if args and kwargs:
                    e(*args, **kwargs)
                elif args:
                    e(*args)
                elif kwargs:
                    e(**kwargs)
                else:
                    e()
        if event in self._ctxevent_listeners:
            for e in self._ctxevent_listeners[event]:
                if args and kwargs:
                    e(self, *args, **kwargs)
                elif args:
                    e(self, *args)
                elif kwargs:
                    e(self, **kwargs)
                else:
                    e(self)
    
    def get_handler(self, idx):
        try:
            return self._handlers[idx-1]
        except IndexError:
            return None

def element(tag=None, registry=element_registry):
    def element_decorate(func):
        _register_element(func, tag, registry)
        return func
    return element_decorate

def _register_element(element, tag=None, registry=element_registry):
    element_name = tag or element.__name__
    if not hasattr(element, "__call__") and hasattr(element, "render"):
        setattr(element, "__call__", element.render)
    registry.register(element_name, element)

def _parse_element(elem: Element, registry=element_registry, var_ctx=None):
    context = var_ctx or {}
    tag = elem.tag
    constructor = registry.get(tag)
    if not constructor:
        raise ValueError(f"Invalid Element: {tag}")
    
    def replace_elem_text_wvar(match: re.Match[str]):
        key = match.group(1)
        return str(context.get(key, f"{{{key}}}"))

    text = re.sub(r"\{(.*?)\}", replace_elem_text_wvar, str(elem.text.strip() if (elem.text and elem.text.strip()) else ""))
    attrib = {}
    for key, value in elem.attrib.items():
        attrib.update({key: re.sub(r"\{(.*?)\}", replace_elem_text_wvar, value)})
    children = [_parse_element(child, registry, context) for child in elem]

    obj = constructor(tag, text, attrib, children)
    if not hasattr(element, "render") and hasattr(obj, "__call__"):
        setattr(obj, "render", obj.__call__)
    return obj

def get_renderable(elem: Element | str, registry=element_registry, var_ctx=None):
    context = var_ctx or {}
    if hasattr(elem, "render"):
        return elem
    elif isinstance(elem, Element):
        return _parse_element(elem, registry, context)
    elif isinstance(elem, PageXML):
        wrapped = fromstring(elem.txt)
        return get_renderable(_parse_element(wrapped, registry, context))
    else:
        to_wrap = str(elem)
        try:
            wrapped = fromstring(to_wrap)
            return _parse_element(wrapped, registry, context)
        except:
            raw = lambda ctx: to_wrap
            setattr(raw, "render", raw.__call__)
            return raw

element_registry.create_scope("std")
element_registry.push_scope("std")
from .elements import *
element_registry.pop_scope()