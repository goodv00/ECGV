"""
Script to create a menu bar in a tk root window

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-----------------------------------------------
from tkinter import Menu, Tk
from modules.root_window import RootWindow
from modules.gui_elements import ThemedMenu

# Static functions -------------------------------------------
def create_menu_items(root_menu: Menu, menu_items: dict[str, type(callable) | None]) -> None:
    """
    Function that takes a dict to specify menu and menu items to load menu and functions on screen
    :param root_menu:
    :param menu_items:
    :return:
    """
    for key, menu_command in menu_items.items():
        if 'Separator' in key:
            root_menu.add_separator()
        else:
            if menu_command is None:
                continue
            root_menu.add_command(command=menu_command, label=key)


# Classes ----------------------------------------------------
class MenuBar:
    def __init__(self, root_window: RootWindow | Tk, items: dict[str, dict[str, type(callable) | None]]) -> None:
        self.main_menu = ThemedMenu(root_window)
        root_window.config(menu=self.main_menu)
        self.menu_bar_items = {}
        self.create_menu(items=items)

    def create_menu(self, items: dict[str, dict[str, type(callable) | None]]) -> None:
        for sub_menu_key, sub_menu_dict in items.items():
            self.menu_bar_items[sub_menu_key] = ThemedMenu(self.main_menu)
            create_menu_items(root_menu=self.menu_bar_items[sub_menu_key], menu_items=sub_menu_dict)
            self.main_menu.add_cascade(label=sub_menu_key, menu=self.menu_bar_items[sub_menu_key])


