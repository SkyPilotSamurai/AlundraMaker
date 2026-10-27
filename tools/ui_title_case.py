"""Title Case for every menu, button, check box and radio option (user request 2026-10-07).

install() wraps the Tk widget classes once, before the editor builds its UI,
so labels written anywhere in the code are shown with the first letter of
each word capitalised ("Save mod as..." -> "Save Mod As..."). Only lowercase
word starts change; "BizHawk", "DATAS" and text after an apostrophe keep
their case. Plain labels, help text and list contents are not changed.
"""
import re
import tkinter as tk
from tkinter import ttk

_WORD_START = re.compile(r"(?<![\w'’])([a-z])")


def title_case(text):
    if not isinstance(text, str):
        return text
    return _WORD_START.sub(lambda m: m.group(1).upper(), text)


def _fix(kw, key):
    if key in kw:
        kw[key] = title_case(kw[key])
    return kw


def _wrap_widget(module, name):
    base = getattr(module, name)
    if getattr(base, '_title_case', False):
        return

    def __init__(self, master=None, cnf=None, **kw):
        if cnf:
            cnf = _fix(dict(cnf), 'text')
        _fix(kw, 'text')
        if cnf:
            base.__init__(self, master, cnf, **kw)
        else:
            base.__init__(self, master, **kw)

    def configure(self, cnf=None, **kw):
        if isinstance(cnf, dict):
            cnf = _fix(dict(cnf), 'text')
        _fix(kw, 'text')
        return base.configure(self, cnf, **kw)

    wrapped = type(name, (base,), {'__init__': __init__, 'configure': configure,
                                   'config': configure, '_title_case': True,
                                   '__module__': base.__module__})
    setattr(module, name, wrapped)


def _wrap_menu():
    if getattr(tk.Menu, '_title_case', False):
        return
    base = tk.Menu

    def adder(method):
        original = getattr(base, method)

        def call(self, *args, **kw):
            if args and isinstance(args[0], dict):
                args = (_fix(dict(args[0]), 'label'),) + args[1:]
            return original(self, *args, **_fix(kw, 'label'))
        return call

    def insert(method):
        original = getattr(base, method)

        def call(self, index, cnf=None, **kw):
            if cnf is None and not kw:
                return original(self, index)   # query: returns the entry's options
            if isinstance(cnf, dict):
                cnf = _fix(dict(cnf), 'label')
            return original(self, index, cnf if cnf is not None else {}, **_fix(kw, 'label'))
        return call

    names = {m: adder(m) for m in ('add_command', 'add_cascade', 'add_checkbutton', 'add_radiobutton')}
    names.update({m: insert(m) for m in ('insert_command', 'insert_cascade', 'insert_checkbutton',
                                         'insert_radiobutton', 'entryconfigure', 'entryconfig')})
    names['_title_case'] = True
    names['__module__'] = base.__module__
    tk.Menu = type('Menu', (base,), names)


def install():
    for name in ('Button', 'Checkbutton', 'Radiobutton', 'Menubutton'):
        _wrap_widget(ttk, name)
        _wrap_widget(tk, name)
    _wrap_menu()
