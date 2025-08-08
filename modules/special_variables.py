"""
Classes to create special variables to work across all tabs in the app

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-------------------------------------------
from tkinter import StringVar

# Import functions from other scripts-----------------------
from modules.data_handler import DataHandler

# Global variables------------------------------------------

# Static functions -----------------------------------------

# Classes---------------------------------------------------
class SelectedLabel(StringVar):
    def __init__(self, *args, data_handler: DataHandler, **kwargs) -> None:
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)

    def assign(self, value: str) -> None:
        # We need this function so the DataHandler stays free from tkinter dependencies
        self.set(value)
        self.data_handler.set_selected_label(value)

    def sync(self):
        # Used when you jump from one tab to another and data_handler instance becomes another than this classes
        self.data_handler.set_selected_label(self.get())


class YAxis(StringVar):
    def __init__(self, *args, data_handler: DataHandler, **kwargs) -> None:
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)

    def assign(self, value: str) -> None:
        # We need this function so the DataHandler stays free from tkinter dependencies
        self.set(value)
        self.data_handler.y_axis_header = value

class XAxis(StringVar):
    def __init__(self, *args, data_handler: DataHandler, **kwargs) -> None:
        self.data_handler = data_handler
        super().__init__(*args, **kwargs)

    def assign(self, value: str) -> None:
        # We need this function so the DataHandler stays free from tkinter dependencies
        self.set(value)
        self.data_handler.x_axis_header = value

