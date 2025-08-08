"""
Holds all themed gui elements used in this app

Author: Victor Gutgesell
Version: 1.0
"""
# Import packages-------------------------------------------
from tkinter import Menu, PanedWindow, Scale, LabelFrame, Button, Checkbutton, Radiobutton, Entry, Label, Frame
from tkinter import HORIZONTAL
from tkinter.ttk import OptionMenu

# Global variables------------------------------------------
MASTER_FONT = ('Arial', 9)
MASTER_COLORS = {
    'fg':             "#000000",
    'bg':             "#ffffff",
    'disabledfg':     "#737373",
    'disabledbg':     "#ffffff",
    'selectfg':       "#ffffff",
    'selectbg':       "#DEE6E8",
}


# Classes here are themed versions of tkinter widgets
# See tkinter documentation for more information
# Classes---------------------------------------------------
class ThemedMenu(Menu):
    def __init__(self, *args, **kwargs):

        self.style = {
            'font': (MASTER_FONT[0], 9),
            'bg': MASTER_COLORS['bg'],
        }

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)


class ThemedPanedWindow(PanedWindow):
    def __init__(self, *args, **kwargs):

        self.style = {
            'bd': 2,
            'bg': MASTER_COLORS['bg'],
            'relief': 'flat',  # must be flat, groove, raised, ridge, solid, or sunken
            'handlepad': 0,
        }

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)


class ThemedScale(Scale):
    def __init__(self, *args, **kwargs):

        self.style = {
            'bg': MASTER_COLORS['bg'],
            'fg': MASTER_COLORS['fg'],
            'orient': HORIZONTAL,
            'bd': 1,
            'showvalue': False,
            'troughcolor': MASTER_COLORS['selectbg'],
            'sliderrelief': 'raised',
            'activebackground': MASTER_COLORS['bg'],
            'highlightthickness': 0,
        }

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)


class ThemedLabelFrame(LabelFrame):
    def __init__(self, *args, **kwargs):
        self.style = {
            # Style kwargs for frames
            'bd': 1,
            'bg': MASTER_COLORS['bg'],
            'fg': MASTER_COLORS['fg'],
            'relief': 'flat',  # must be flat, groove, raised, ridge, solid, or sunken
            'padx': 2,
            'pady': 2,
        }
        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)


class ThemedFrame(Frame):
    def __init__(self, *args, **kwargs):
        self.style = {
            # Style kwargs for frames
            'bd': 2,
            'bg': MASTER_COLORS['bg'],
            'relief': 'flat',  # must be flat, groove, raised, ridge, solid, or sunken
        }
        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)

class ThemedButton(Button):
    def __init__(self, *args, **kwargs):
        self.style = {
            # Style kwargs for buttons
            'anchor': 'w',  # must be n, ne, e, se, s, sw, w, nw, or center
            'highlightbackground': MASTER_COLORS['selectbg'],
            'highlightcolor': MASTER_COLORS['selectfg'],
            'activebackground': MASTER_COLORS['selectbg'],
            'bd': 1,
            'bg': MASTER_COLORS['bg'],
            'fg': MASTER_COLORS['fg'],
            'cursor': 'hand2',
            'disabledforeground': MASTER_COLORS['disabledfg'],
            'font': MASTER_FONT,
            'justify': 'center',
            'overrelief': 'ridge',  # must be flat, groove, raised, ridge, solid, or sunken
            'padx': 5,
            'pady': 5,
        }
        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)

class ThemedRadiobutton(Radiobutton):
    def __init__(self, *args, **kwargs):
        self.style = {
            'indicator': 0,
            'background': MASTER_COLORS['bg'],
            'activebackground': MASTER_COLORS['selectbg'],
        }

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)

class ThemedCheckbutton(Checkbutton):
    def __init__(self, *args, **kwargs):
        self.style = {
            'indicator': 0,
            'cursor': 'hand2',
            'background': MASTER_COLORS['bg'],
            'fg': 'black',
            'selectcolor': MASTER_COLORS['selectbg'],
        }
        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)

class ThemedEntry(Entry):
    def __init__(self, *args, **kwargs):

        self.style = {'width': 20,
                      'bg': MASTER_COLORS['bg'],
                      'fg': MASTER_COLORS['fg'],
                      'cursor': 'xterm',
                      'highlightbackground': MASTER_COLORS['disabledbg'],
                      'selectbackground': MASTER_COLORS['selectbg'],
        }

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)

class ThemedLabel(Label):
    def __init__(self, *args, **kwargs):
        self.style = {
            # Style kwargs for frames
            'bd': 1,
            'bg': MASTER_COLORS['bg'],
            'fg': MASTER_COLORS['fg'],
            'relief': 'flat',  # must be flat, groove, raised, ridge, solid, or sunken
            'padx': 2,
            'pady': 2,
        }
        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)


class ThemedOptions(OptionMenu):
    def __init__(self, *args, **kwargs):
        self.style = {}

        for key in self.style.keys():
            if key not in kwargs:
                kwargs[key] = self.style[key]

        super().__init__(*args, **kwargs)