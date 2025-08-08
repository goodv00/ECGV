"""
Mster slider handler class. Takes care of the slider for the graph

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages ------------------------------------------
from tkinter import IntVar, BOTH, DoubleVar

# Import functions from other scripts ----------------------
from modules.gui_elements import  ThemedScale

# Classes --------------------------------------------------

class MasterSlider(ThemedScale):
    def __init__(self, master, var: IntVar | DoubleVar, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.var = var
        self.configure(variable=self.var)
        self.pack(fill=BOTH)

    def update_slider(self, data_length: float, window_size: float, location: float):
        slider_length = int(self.winfo_width() * window_size / data_length)
        if slider_length <= 5:
            slider_length = 10
        self.configure(to=data_length, sliderlength=slider_length)
        self.var.set(location)

