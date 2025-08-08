"""
Main file for CSV Viewer. Run this script to initiate the application.

Author: Victor Gutgesell
Version: 1.0
Home: https://github.com/goodv00/CSV-Viewer-App
"""
from tkinter.ttk import Notebook

# Import packages-----------------------------------------------
from tkinter import messagebox

# Import functions from other scripts-----------------------
from modules.root_window import RootWindow
from modules.menu_bar import MenuBar
from modules.gui_elements import ThemedFrame
from modules.data_handler import DataHandler
from modules.pop_ups import InputBox
from screens.annotation_screen import AnnotationScreen
from screens.interval_viewer_screen import IntervalScreen


# Static functions -------------------------------------------

# Classes ----------------------------------------------------
class App(RootWindow):
    def __init__(self):
        super().__init__(title='ECG Viewer for Polar H10')
        # Loading special variables across all tabs
        self.master_location = None
        self.data_handler = DataHandler()
        self.data_handler.in_app = True

        # Getting menu
        self.menu = None
        self.menu_bar_items = None
        self.load_menu_bar()

        # Creating tabs
        self.notebook = Notebook(self)
        self.notebook.pack(fill='both', expand=True)

        self.tab_frames = {'Annotation': ThemedFrame(self.notebook),
                           'Interval': ThemedFrame(self.notebook)}

        self.child_screens = {'Annotation': AnnotationScreen(self.tab_frames['Annotation'], self.data_handler),
                              'Interval': IntervalScreen(self.tab_frames['Interval'], self.data_handler)}

        for text, frame in self.tab_frames.items():
            frame.pack(fill='both', expand=True)
            self.notebook.add(frame, text=text)

        self.notebook.bind('<Leave>', self.on_leave)
        self.notebook.bind('<Enter>', self.on_enter)
        self.notebook.bind('<Button>', self.on_click)

    def load_menu_bar(self):
        # Configuring the main menu
        self.menu_bar_items = {
            'File': {
                'Open...': self.open_file_sequence,
                'Save...': self.data_handler.save_file,
                'Save as...': self.save_file_as_sequence,
                'Separator_1': None,
                'Reload project': self.reload_project,
                'Separator_2': None,
                'Exit': self.destroy,
            },
            'Edit': {
                'Create Label': lambda: InputBox(title='Define new label', enter_action=self.create_label),
                'Separator_1': None,
                'Set file delimiter': self.set_delimiter,
            }
        }
        self.menu = MenuBar(self, self.menu_bar_items)

    # Menu functionality ---------------------------------
    def open_file_sequence(self) -> None:
        """
        Method to open a file dialog to select a file and plot it on the main graph.
        :return: None
        """
        if self.data_handler.plot_data is not None:
            response = messagebox.askokcancel('Load Project...', 'Loading the project will delete all unsaved changes. Continue?')
            if not response:
                return
        self.data_handler.get_and_open_file()
        self.child_screens['Annotation'].load_project()
        self.child_screens['Interval'].load_project()

    def load_project(self) -> None:
        """
        Method to load a project into graph
        :return:
        """
        self.data_handler.open_file()
        # Needs code to initiate file in all tabs
        self.child_screens['Annotation'].load_project()
        self.child_screens['Interval'].load_project()

    def save_file_as_sequence(self) -> None:
        """
        Method to save the currently opened file as csv.
        :return: None
        """
        try:
            self.data_handler.save_file_as()
        except ValueError as e:
            messagebox.showinfo(title='Error', message=str(e))

    def reload_project(self):
        """
        Method to reload the graph.
        :return:
        """
        if not messagebox.askokcancel(title='Warning', message='Reload graph? All changes will be lost...'):
            return
        self.load_project()

    def create_label(self, label: str):
        """
        Method to create a new label
        :return:
        """
        try:
            self.child_screens['Annotation'].create_label(label)
        except ValueError as e:
            messagebox.showerror(title='Error', message=str(e))

    def set_delimiter(self):
        """
        Method to set the delimiter of the DataHandler
        :return:
        """
        InputBox(title='Set delimiter...', enter_action=self.data_handler.set_delimiter)

    def on_enter(self, event):
        return

    def on_leave(self, event):
        return

    def on_click(self, event):
        """
        Method to use on click on one of the tab-bars. Makes sure that all screens are updated when changing tabs.
        :param event:
        :return:
        """
        if self.data_handler.plot_data is None:
            return

        old_tab = list(self.child_screens.keys())[self.notebook.index('current')]
        self.master_location = self.child_screens[old_tab].graph_handler.master_location.get()

        for tab, child in self.child_screens.items():
            if tab == old_tab:
                continue
            if self.child_screens[old_tab].changes:
                self.child_screens[tab].refresh_graph()
            self.child_screens[tab].update_options()
            self.child_screens[tab].graph_handler.move_to(self.master_location)
        self.child_screens[old_tab].changes = False


# Run code------------------------------------------------------
if __name__ == '__main__':
    app = App()
    app.mainloop()
