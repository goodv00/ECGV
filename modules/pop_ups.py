"""
Code used to create a pop-up window class with tkinter

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-------------------------------------------
from tkinter import *
from tkinter import messagebox
from modules.gui_elements import *
from modules.root_window import RootWindow

# Classes---------------------------------------------------
class PopUp(RootWindow):
    """
    Class that creates different types of pop-up windows for user inputs
    """
    def __init__(self, title: str, **kwargs: any):
        super().__init__(title=title, state='normal', **kwargs)
        self.attributes('-topmost', True)
        self.pop_up_elements = None

class InputBox(PopUp):
    """
    Class that creates a pop-up window for user text inputs
    """
    def __init__(self, title: str, enter_action: callable, geometry: str | None = None, **kwargs: any):
        """
        :param title: Title of the PopUp window
        :param enter_action: Callable that takes a string as an argument. Action done upon hitting 'Enter'
        :param geometry: Geometry of the PopUp window
        :param kwargs:
        """
        super().__init__('Enter value...', **kwargs)
        self.config(bg='white')
        if geometry is not None:
            self.geometry(geometry)
        self.enter_action = enter_action

        config = {
            'Label': (title, lambda: None, {}),
            'Input': ('', lambda: None, {}),
            'Enter': ('Enter', self.enter_value, {}),
            'Cancel': ('Cancel', self.cancel, {}),
        }
        self.pop_up_elements = {
            'Label': ThemedLabel(self, text=config['Label'][0]),
            'Input': ThemedEntry(self, width=40, **config['Input'][2]),
            'Enter': ThemedButton(self, text=config['Enter'][0], command=config['Enter'][1], width=12),
            'Cancel': ThemedButton(self, text=config['Cancel'][0], command=config['Cancel'][1], width=12),
        }
        # Set-up on screen
        self.pop_up_elements['Label'].grid(row=0, column=0, columnspan=2, sticky=W, padx=20)
        self.pop_up_elements['Input'].grid(row=1, column=0, columnspan=2, sticky=W, ipadx=10, padx=20)
        self.pop_up_elements['Enter'].grid(row=2, column=0, sticky=W, padx=20, pady=5, ipady=2),
        self.pop_up_elements['Cancel'].grid(row=2, column=1, sticky=W, padx=5, pady=5, ipady=2)
        self.mainloop()

    def enter_value(self):
        if not (self.pop_up_elements['Input'].get() == ''):
            self.enter_action(self.pop_up_elements['Input'].get())
            self.destroy()
        else:
            messagebox.showwarning('Warning', 'Please enter a label name')
            self.attributes('-topmost', True)

    def cancel(self):
        self.destroy()


# Testing ---------------------------------------------------------------------
if __name__ == '__main__':
    InputBox(title='Hello', enter_action=lambda x: print(x))
