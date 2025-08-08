"""
Code used to create a root window class with tkinter

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-------------------------------------------
from tkinter import Tk

# Classes---------------------------------------------------
class RootWindow(Tk):
    def __init__(self, title: str, state: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title(title)
        if state is not None:
            self.state(state)
        self.config()

        # Dummy variables
        self.resolution = None
        self.height = None
        self.width = None

    def get_resolution(self) -> None:
        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        self.resolution = f'{self.width}x{self.height}'


# Testing--------------------------------------------------
if __name__ == '__main__':
    root = RootWindow('CSV-Viewer', 'zoomed')
    root.mainloop()
