"""
Filter screen. Run this script to open the screen that lets you apply filters to the ECG recording.

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-----------------------------------------------
from tkinter import Tk, Frame, HORIZONTAL, VERTICAL, BOTH, LEFT
from tkinter.ttk import Notebook

# Import functions from other scripts-----------------------
from modules.data_handler import DataHandler
from modules.graph_handler import GraphHandler
from modules.gui_elements import ThemedPanedWindow, ThemedLabelFrame, ThemedFrame, ThemedLabel


# Statis functions -------------------------------------------

# Classes ----------------------------------------------------
class TwoPanelTemplate:
    def __init__(self, screen_root: Tk | Notebook | Frame, app_data_handler: DataHandler):
        self.on_screen_title = None
        self.root = screen_root
        self.options_panel_frames = None
        self.main_graph_slider = None
        self.main_screen_panels = None

        # Special variables
        self.data_handler = app_data_handler
        self.data_handler.in_app = True

        # Initiating the graph
        self.main_screen_panels = {
            'Parent': ThemedPanedWindow(self.root, orient=HORIZONTAL, bg='#DEE6E8'),
            'Children': {
                'Options Panel': ThemedPanedWindow(self.root, orient=VERTICAL),
                'Graph Panel': ThemedPanedWindow(self.root),
            }
        }

        self.main_screen_panels['Parent'].pack(fill=BOTH, expand=True)
        for _, value in self.main_screen_panels['Children'].items():
            self.main_screen_panels['Parent'].add(value)

        self.main_panel_frames = {
            'Options': ThemedFrame(self.main_screen_panels['Children']['Options Panel']),
            'Title': ThemedFrame(self.main_screen_panels['Children']['Graph Panel']),
            'Graph': ThemedFrame(self.main_screen_panels['Children']['Graph Panel']),
        }

        self.main_panel_frames['Options'].pack(fill=BOTH)
        self.main_panel_frames['Title'].pack(fill=BOTH)
        self.main_panel_frames['Graph'].pack(fill=BOTH, expand=True)

        # Other handler classes
        self.graph_handler = GraphHandler(self.main_panel_frames['Graph'])
        self.graph_handler.create_master_slider()

        # Defining the dummy click actions - specify what the graph should do on left and right click
        self.graph_handler.injected_actions['left_select'] = lambda event: None
        self.graph_handler.injected_actions['right_select'] = lambda event: None
        self.graph_handler.injected_actions['middle_select'] = lambda event: None

        # Default title
        self.set_title('No data loaded...')

    def load_options_panel(self, label_frame_list: list[str]):
        self.options_panel_frames = {}
        for label_frame in label_frame_list:
            frame = ThemedLabelFrame(self.main_panel_frames['Options'], text=label_frame)
            self.options_panel_frames[label_frame] = frame
            frame.pack(fill=BOTH, expand=True, pady=3)

    def set_title(self, title: str) -> None:
        """
        Method to set the on-screen title
        :param title:
        :return:
        """
        if self.on_screen_title is not None:
            self.on_screen_title.destroy()
        self.on_screen_title = ThemedLabel(self.main_panel_frames['Title'], text=title, font=('Arial', 14, 'bold'))
        self.on_screen_title.pack(ipadx=30, ipady=20, anchor='w')
