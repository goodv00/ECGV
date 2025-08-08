"""
Filter screen. Run this script to open the screen that lets you apply filters to the ECG recording.

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-----------------------------------------------
from tkinter import Tk, Frame, BOTH, StringVar, messagebox, IntVar
from tkinter.ttk import Notebook

import pandas as pd
from matplotlib.backend_bases import MouseEvent
from numpy import sort, array
from pandas import DataFrame

# Import functions from other scripts-----------------------
from modules.data_handler import DataHandler
from modules.special_variables import YAxis, SelectedLabel, XAxis
from modules.gui_elements import ThemedOptions, ThemedButton, ThemedCheckbutton
from modules.root_window import RootWindow
from analysis.ecg_toolbox import get_pulse_metrics, get_anomalies_from_rri, frequency_filtering_butterworth
from screens.paned_screen_templates import TwoPanelTemplate
from modules.graph_handler import get_axis_geometry, find_closest_point, legend_without_duplicate_labels
from utils.helpers import get_default_annotations

# Global Variables -------------------------------------------
OPTION_BUTTON_ALIGNMENT = {
    'Take Screenshot': {'column': 0, 'row': 0, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Backward': {'column': 0, 'row': 1, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Forward': {'column': 1, 'row': 1, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Move_to': {'column': 0, 'row': 2, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Move_to_input': {'column': 0, 'row': 3, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Zoom out': {'column': 0, 'row': 4, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
}
DEFAULT_HEARTBEAT_CLASSES = get_default_annotations()['heartbeat_classes']
SEGMENT_DENOMINATORS = get_default_annotations()['segment_denominators']
COLOR_PALETTE = get_default_annotations()['standard_colors']


# Static functions -------------------------------------------

# Classes ----------------------------------------------------
class IntervalScreen(TwoPanelTemplate):
    """
    Screen to display raw ECG, RR plot and HR plot.
    This screen is supposed to help identify anomalies in RR intervals. It is particularly useful to detect
    premature atrial contractions (PACs). Since the location of the main plot is passed from one tab to another
    you can easily locate the PACs in this screen and jump back to annotation to select the datapoint.

    ---------------------------------
    |                               |
    |           Raw ECG             |
    |                               |
    ---------------------------------
    ---------------------------------
    |            RR plot            |
    ---------------------------------
    ---------------------------------
    |            HR plot            |
    ---------------------------------

    This screen features 3 axes in the figure that do not share an x-axis. RR and HR are centered around the center of
    the Raw ECG plot, and you can click them to change the displayed location in the Raw ECG plot.

    """

    def __init__(self, screen_root: Tk | Notebook | Frame, app_data_handler: DataHandler):
        super().__init__(screen_root, app_data_handler)
        self.changes = False
        self.on_screen_browser = None
        self.move_to_boxes = None
        self.menu = None
        self.menu_bar_items = None
        self.on_screen_actions = None
        self.on_screen_options = None
        self.y_axis_selector = None
        self.x_axis_selector = None
        self.label_selector = None
        self.r_peak_selector = None
        self.anomalies = []
        self.center_last_selection = IntVar()
        self.snap_on_max = IntVar()
        self.snap_on_max.set(1)

        # Special variables
        self.selected_label = SelectedLabel(self.root, self.data_handler.selected_label, data_handler=self.data_handler)
        self.y_axis_label = YAxis(self.root, self.data_handler.y_axis_header, data_handler=self.data_handler)
        self.x_axis_label = XAxis(self.root, self.data_handler.x_axis_header, data_handler=self.data_handler)

        # Adjusting the figure so it fits this view
        self.graph_handler.snap_on_max = self.snap_on_max
        self.graph_handler.use_grid_spec(shape=(5, 1), specs=[(slice(0, 3), 0), (3, 0), (4, 0)],
                                         sharex=[None, None, (3, 0)], hspace=0.1)
        self.graph_handler.key_actions_on_master_only = True
        self.graph_handler.axes[self.graph_handler.master_axis].xaxis.set_ticks_position('top')
        self.graph_handler.figure.subplots_adjust(top=0.95, bottom=0.1)
        self.graph_handler.axes[3, 0].xaxis.set_visible(False)

        # Defining the injected actions
        self.graph_handler.injected_actions['left_select'] = self.left_click
        self.graph_handler.injected_actions['move'] = self.update_interval_information
        self.graph_handler.injected_actions['zoom'] = self.update_interval_information

        # Initiate all elements
        self.load_options_panel(
            ['Options', 'Actions', 'Y-Axis', 'X-Axis', 'Selection label']
        )
        self.load_on_screen_axis_selector()
        self.load_on_screen_label_selector(var=self.selected_label)
        self.load_on_screen_options()

        # Loading buttons and options
        self.load_action_buttons()

    """
    Methods to create the screen elements and layouts
    """

    def load_action_buttons(self):

        entry_var = StringVar()
        entry_var.set('0')

        self.on_screen_actions = {
            'Take Screenshot': ThemedButton(self.options_panel_frames['Actions'], text='Take Screenshot'),
            'Backward': ThemedButton(self.options_panel_frames['Actions'], text='Backward'),
            'Forward': ThemedButton(self.options_panel_frames['Actions'], text='Forward'),
            'Zoom out': ThemedButton(self.options_panel_frames['Actions'], text='Zoom out'),
        }

        action_variables = {
            'Take Screenshot': self.graph_handler.take_screenshot,
            'Backward': lambda: self.graph_handler.move_backward(),
            'Forward': lambda: self.graph_handler.move_forward(),
            'Zoom out': lambda: self.graph_handler.show_x_window(self.data_handler['Index'][0],
                                                                 self.data_handler['Index'][-1]),
        }

        # Required so the buttons scale with the panel after resizing
        self.options_panel_frames['Actions'].columnconfigure(0, weight=1)
        self.options_panel_frames['Actions'].columnconfigure(1, weight=1)

        for key, value in self.on_screen_actions.items():
            value.grid(**OPTION_BUTTON_ALIGNMENT[key])
            value.configure(command=action_variables[key])

    def load_on_screen_axis_selector(self):
        if self.y_axis_selector is not None:
            self.y_axis_selector.destroy()
        self.y_axis_selector = ThemedOptions(self.options_panel_frames['Y-Axis'],
                                             self.y_axis_label,
                                             self.y_axis_label.get(),
                                             *self.data_handler.plottable_axes,
                                             command=self.select_y_axis)
        self.y_axis_selector.pack(padx=5, pady=2, anchor='w', fill=BOTH)

        if self.x_axis_selector is not None:
            self.x_axis_selector.destroy()
        self.x_axis_selector = ThemedOptions(self.options_panel_frames['X-Axis'],
                                             self.x_axis_label,
                                             self.x_axis_label.get(),
                                             *self.data_handler.time_axes + ['Index'],
                                             command=self.select_x_axis)
        self.x_axis_selector.configure(width=20)
        self.x_axis_selector.pack(padx=5, pady=2, anchor='w', fill=BOTH)

    def load_on_screen_label_selector(self, var: StringVar):
        """
        Method to load the dropdown menu to get the selected label
        :param var: SelectedLabel var
        :return:
        """
        if self.label_selector is not None:
            self.label_selector.destroy()

        # Doing it this way automatically removes duplicates....
        label_list = list({**dict.fromkeys(self.data_handler.label_list),
                           **DEFAULT_HEARTBEAT_CLASSES,
                           **SEGMENT_DENOMINATORS})

        for num, label in enumerate(label_list.copy()):
            if label in DEFAULT_HEARTBEAT_CLASSES:
                label_list[num] = f'{label}: {DEFAULT_HEARTBEAT_CLASSES[label]}'
            elif label in SEGMENT_DENOMINATORS:
                label_list[num] = f'{label}: {SEGMENT_DENOMINATORS[label]}'
            else:
                continue

        self.label_selector = ThemedOptions(self.options_panel_frames['Selection label'],
                                            var,
                                            var.get(),
                                            *label_list,
                                            command=lambda x: self.selected_label.assign(x.split(': ')[0]))
        self.label_selector.pack(padx=5, pady=5, anchor='w', fill=BOTH)

    def load_on_screen_options(self):
        """
        Loading the toggle buttons for selection options
        :return:
        """
        self.on_screen_options = {
            'Snap': ThemedCheckbutton(self.options_panel_frames['Options'],
                                      text='Snap on local max'),
            'Center': ThemedCheckbutton(self.options_panel_frames['Options'],
                                        text='Center on selection'),
        }
        options_variables = {
            'Snap': self.snap_on_max,
            'Center': self.center_last_selection
        }

        for key, value in self.on_screen_options.items():
            value.pack(padx=5, pady=2, anchor='w', fill=BOTH)
            value.configure(variable=options_variables[key])

    """
    Methods to initiate and manage in-app data (also used by main script)
    """

    def refresh_graph(self) -> None:
        """
        Method to refresh the graph
        :return:
        """
        if self.data_handler.plot_data is None:
            return

        x_column = self.x_axis_label.get()
        y_column = self.y_axis_label.get()
        args = (self.data_handler[x_column], self.data_handler[y_column])
        filtered_signal = frequency_filtering_butterworth(self.data_handler[y_column], 130, upper=40, lower=0.5)

        # Plotting the raw signal in line-plot
        kwargs = {'name': y_column, 'label': 'Raw signal', 'color': 'k', 'linewidth': 2}
        self.graph_handler.plot_line_plot(*args, **kwargs)

        # Plotting a filtered signal in line-plot (BPF 0.5-40Hz)
        kwargs = {'name': 'filtered', 'label': 'Filtered 0.5Hz-40Hz', 'color': 'r', 'linewidth': 0.3}
        self.graph_handler.plot_line_plot(self.data_handler[x_column], filtered_signal, **kwargs)

        # Plotting all label information
        self.plot_all_label_information()

        # Setting axis names
        self.graph_handler.axes[self.graph_handler.master_axis].set_ylabel(y_column)
        self.graph_handler.axes[self.graph_handler.master_axis].set_xlabel(x_column)

        # Filling the secondary axes
        self.display_rri_and_hr_graph()
        self.update_interval_information()
        self.graph_handler.refresh(zoom=True)

    def update_options(self) -> None:
        """
        Method to update the tab when switching into it
        :return: None
        """
        self.selected_label.sync()
        self.display_rri_and_hr_graph()
        self.load_on_screen_axis_selector()
        self.load_on_screen_label_selector(self.selected_label)

    def load_project(self) -> None:
        """
        Method to load a project into graph
        :return:
        """
        self.graph_handler.reset(reset_window=True, reset_custom_labels=True)
        self.set_title(self.data_handler.filename)
        self.selected_label.set(self.data_handler.selected_label)
        self.y_axis_label.set(self.data_handler.y_axis_header)
        self.x_axis_label.set(self.data_handler.x_axis_header)
        self.select_x_axis(self.x_axis_label.get())
        self.load_on_screen_axis_selector()
        self.load_on_screen_label_selector(self.selected_label)
        self.refresh_graph()

    """
    Actions tied to some on-screen functionality
    """

    def select_y_axis(self, col: str) -> None:
        self.y_axis_label.assign(col)
        self.refresh_graph()

    def select_x_axis(self, col: str) -> None:
        # Need to replot everything....
        self.x_axis_label.assign(col)
        self.graph_handler.reset(reset_window=False, reset_custom_labels=True)
        self.refresh_graph()

        if col.lower() == 'index':
            return

        else:
            col = self.data_handler[col]
            labels = col.values
            locs = col.values
            self.graph_handler.show_ecg_grid(labels=labels, locs=locs)

    """
    Methods used to fill the plot
    """

    def plot_all_label_information(self) -> None:
        """
        Method to plot all label information
        :return:
        """
        # Plotting the label information
        for label in self.data_handler.label_list:
            if label in SEGMENT_DENOMINATORS:
                self.plot_segment_information(label)
            else:
                self.scatter_plot_label_information(label)

    def plot_segment_information(self, label):
        """
        Method used to show segment information
        :return:
        """

        x_span, y_span, _, _, ar = get_axis_geometry(self.graph_handler.axes[self.graph_handler.master_axis])
        label_data = self.data_handler.get_label_data(label)
        if label_data.empty:
            return
        x_locs = label_data[self.x_axis_label.get()].values
        y_locs = label_data[self.y_axis_label.get()].values + y_span * 0.08

        if label in COLOR_PALETTE:
            color = COLOR_PALETTE[label]
        else:
            color = '#FC8282'

        for num, x_loc in enumerate(x_locs):
            args = (x_loc, y_locs[num], label)
            kwargs = {'name': f'segments_{label}_{num}', 'axis_selector': self.graph_handler.master_axis,
                      'backgroundcolor': color}
            self.graph_handler.plot_text(*args, **kwargs, fontsize=8)
        args = (x_locs, label_data[self.y_axis_label.get()].values, y_locs)
        kwargs = {'name': f'segments_{label}', 'axis_selector': self.graph_handler.master_axis,
                  'color': color, 'linewidth': 2, 'linestyle': 'dashed'}
        self.graph_handler.plot_vlines(*args, **kwargs)
        args = (x_locs, label_data[self.y_axis_label.get()].values)
        kwargs = {'name': f'segments_{label}', 'axis_selector': self.graph_handler.master_axis,
                  'label': f'{label}: {SEGMENT_DENOMINATORS[label]}',
                  'color': color}
        self.graph_handler.plot_scatter_plot(*args, **kwargs)

    def scatter_plot_label_information(self, label: str) -> None:
        """
        Method to plot singular label information.
        :param label:
        :return:
        """

        label_data = self.data_handler.get_label_data(label)
        if label_data.empty:
            return
        args = (label_data[self.x_axis_label.get()], label_data[self.y_axis_label.get()])
        try:
            display_label = f'{label}: {DEFAULT_HEARTBEAT_CLASSES[label]}'
        except KeyError:
            display_label = label
        kwargs = {'name': f'label_{label}', 'label': display_label, 'axis_selector': self.graph_handler.master_axis}
        if label in COLOR_PALETTE:
            kwargs['color'] = COLOR_PALETTE[label]
        self.graph_handler.plot_scatter_plot(*args, **kwargs)

    def display_rri_and_hr_graph(self):

        self.graph_handler.remove_all_lines(name_filter='ld_')
        self.graph_handler.remove_all_vlines(name_filter='ld_')

        # Loads intervals and hrv
        heartbeat_segments = self.data_handler.get_heartbeats()
        if len(heartbeat_segments) == 0:
            return

        pulse_metrics = []
        for heartbeats in heartbeat_segments:
            pulse_metrics.append(get_pulse_metrics(heartbeats['sensor timer [s]']))

        pulse_metrics = pd.concat(pulse_metrics)

        if len(pulse_metrics) <= 10:
            return

        self.anomalies = get_anomalies_from_rri(pulse_metrics['intervals [s]'], rise_threshold=0.25, drop_threshold=-0.15)
        self.anomalies = self.data_handler[self.x_axis_label.get()][self.anomalies]

        # Sets plot limit on main axis and re-plots the selected label
        an_kwargs = {'name': f'ld_anom',
                     'linestyle': 'dotted', 'color': 'red', 'linewidth': 0.8}
        self.graph_handler.plot_vlines(self.anomalies, -1500, 2000, axis_selector=self.graph_handler.master_axis,
                                       **an_kwargs)

        # Plots RR-intervals dots and vertical lines
        args = (self.data_handler[self.x_axis_label.get()].loc[pulse_metrics.index], pulse_metrics['intervals [s]'])
        kwargs = {'name': f'ld_rri', 'label': 'RRi [s]', 'axis_selector': (3, 0),
                  'linewidth': 0.5, 'color': 'black', 'slider': False}
        self.graph_handler.plot_line_plot(*args, **kwargs)
        self.graph_handler.plot_vlines(self.anomalies, 0, 1000 * 2, axis_selector=(3, 0), **an_kwargs)
        self.graph_handler.axes[kwargs['axis_selector']].set_ylabel('RRi [s]')
        self.graph_handler.axes[kwargs['axis_selector']].set_ylim(0, pulse_metrics['intervals [s]'].max() * 1.1)

        # Plots HR
        HR = 60 / pulse_metrics['intervals [s]']
        args = (self.data_handler[self.x_axis_label.get()].loc[pulse_metrics.index], HR)
        kwargs = {'name': f'ld_HR', 'label': 'HR [bpm]',
                  'axis_selector': (4, 0), 'color': 'black'}
        self.graph_handler.plot_line_plot(*args, slider=False, **kwargs)
        self.graph_handler.plot_vlines(self.anomalies, 0, 1000 * 2, axis_selector=(4, 0), **an_kwargs)
        self.graph_handler.axes[kwargs['axis_selector']].set_ylabel('HR [bpm]')
        self.graph_handler.axes[kwargs['axis_selector']].set_ylim(0, HR.max() * 1.1)

    """
    Injected actions for graph handler
    """

    def left_click(self, event: MouseEvent) -> None:
        """
        Method invoked when clicking left mouse button
        :param event:
        :return:
        """
        if self.data_handler.plot_data is None:
            return
        if event.xdata is None:
            return
        label = self.selected_label.get()
        if self.graph_handler.axis_pointer == self.graph_handler.master_axis:
            # Handle case it clicks on main graph
            self.annotate(event, label)
            self.update_interval_information()
            self.display_rri_and_hr_graph()
        else:
            self.graph_handler.move_to(x_pos=self.graph_handler.hover_coord[0], y_pos=None,
                                       axis_selector=self.graph_handler.master_axis)

    def update_interval_information(self) -> None:
        """
        Method is injected into graph handler's refresh cycle. It does the following:
        1)
        Plot pulse metrics when Heartbeats are present. The method will display the average HR in bpm
        over the visible range of labels, and it will show the RR intervals of several beats on screen when zoomed
        to a certain level
        2)
        Display a rect behind RRi and HR plot to show the window which is currently shown on ECG Plot
        3)
        Center RRi and HR Plot on ecg Plot location

        :return:
        """
        if (self.data_handler.plot_data is None) or not bool(self.data_handler.label_list):
            return

        heartbeat_list = self.data_handler.get_heartbeats()
        time_col = 'sensor timer [s]'

        self.graph_handler.remove_all_text(name_filter='RR_')
        self.graph_handler.remove_all_text(name_filter='HR')
        self.graph_handler.remove_all_text(name_filter='Avg HR')
        self.graph_handler.remove_all_hlines(name_filter='metrics_')
        self.graph_handler.remove_all_vlines(name_filter='metrics_')

        if (len(heartbeat_list) == 0) or (time_col not in self.data_handler.plot_data.columns):
            return

        # Getting axis geometry
        x_span, y_span, x_loc, y_loc, ar = get_axis_geometry(self.graph_handler.axes[self.graph_handler.master_axis])
        ylim = self.graph_handler.axes[self.graph_handler.master_axis].get_ylim()
        xlim = self.graph_handler.axes[self.graph_handler.master_axis].get_xlim()
        xlim_padded = (array(xlim) + array([0.1, -0.1]) * x_span).astype(float)
        center = self.graph_handler.master_location.get()

        kwargs = {
            'heartbeats': None,
            'x_span': x_span,
            'y_span': y_span,
            'x_loc': x_loc,
            'y_loc': y_loc,
            'ar': ar,
            'ylim': ylim,
            'xlim': xlim,
            'xlim_padded': xlim_padded,
            'center': center,
            'time_col': time_col
        }

        self.update_rri_and_hr_location(**kwargs)

        for num, heartbeats in enumerate(heartbeat_list):
            kwargs['heartbeats'] = heartbeats
            self.show_on_screen_hr(num=num, **kwargs)
            self.show_on_screen_intervals(num=num, **kwargs)

    def update_rri_and_hr_location(self, xlim: tuple, x_span: float, x_loc: float, **kwargs):
        # Display the location on the main axis in the RRi Plot and HR plot and fix their y_location
        x = xlim[0]
        y = -50
        height = 1000
        _, y_span_2, _, _, _ = get_axis_geometry(self.graph_handler.axes[3, 0])
        _, y_span_3, _, _, _ = get_axis_geometry(self.graph_handler.axes[4, 0])
        pl_kwargs = {'name': 'loc', 'facecolor': 'lightgreen', 'edgecolor': 'grey'}
        self.graph_handler.plot_box((x, y), x_span, height, axis_selector=(3, 0), **pl_kwargs)
        self.graph_handler.plot_box((x, y), x_span, height, axis_selector=(4, 0), **pl_kwargs)

        # Center RRi plot and HR plot on master location
        self.graph_handler.move_to(x_pos=x_loc, y_pos=y_span_2 * 0.5, axis_selector=(3, 0), refresh=False)
        self.graph_handler.move_to(x_pos=x_loc, y_pos=y_span_3 * 0.5, axis_selector=(4, 0), refresh=False)

    def show_on_screen_hr(self, heartbeats: DataFrame,
                          num: int, time_col: str,
                          ylim: tuple, xlim_padded: tuple, x_span: float, y_span: float, **kwargs) -> None:
        """
        Method to plot on_screen HR information
        :param heartbeats:
        :param num:
        :param time_col:
        :param ylim:
        :param xlim_padded:
        :param x_span:
        :param y_span:
        :return:
        """

        # Computing on-screen metrics
        condition = ((heartbeats[self.x_axis_label.get()] >= xlim_padded[0]) &
                     (heartbeats[self.x_axis_label.get()] <= xlim_padded[1]))
        visible_range = heartbeats.loc[condition]

        # Stop if no on-screen labels
        if len(visible_range) <= 1:
            return
        # Stop if the current segment is too short to see on screen
        if visible_range[self.x_axis_label.get()].diff().sum() <= 0.1 * x_span:
            return

        avg_hr = (60 / visible_range[time_col].diff()).mean()
        # Plotting the heart rate spanner at the bottom of the screen
        y_pos = ylim[0] + y_span * 0.1
        x_pos = visible_range[self.x_axis_label.get()].values[[0, -1]]
        args = (y_pos, *x_pos)
        pl_kwargs = {'name': f'metrics_Avg HR_{num}', 'color': 'grey', 'linestyle': 'dotted'}
        self.graph_handler.plot_hlines(*args, **pl_kwargs)  # This is the dashed horizontal line

        offset = y_span * 0.01
        args = (x_pos, y_pos - offset, y_pos + offset)
        pl_kwargs = {'name': f'metrics_borders_{num}', 'color': 'grey', 'linestyle': 'dotted'}
        self.graph_handler.plot_vlines(*args, **pl_kwargs)  # This is the vertical line
        # Finally plotting the text
        y_pos = y_pos + y_span * 0.01
        x_pos = x_pos[0] + 0.005 * x_span
        self.graph_handler.plot_text(x_pos, y_pos, f'{avg_hr:.0f}bpm', name=f'Avg HR_{num}', fontsize=8)

    def show_on_screen_intervals(self, heartbeats: DataFrame,
                                 num: int, time_col: str, center: float,
                                 ylim: tuple, xlim_padded: tuple, x_span: float, y_span: float, **kwargs) -> None:
        # Computing on-screen metrics
        condition = ((heartbeats[self.x_axis_label.get()] >= xlim_padded[0]) &
                     (heartbeats[self.x_axis_label.get()] <= xlim_padded[1]))
        visible_range = heartbeats.loc[condition]

        if visible_range[self.x_axis_label.get()].diff().mean() <= 0.05 * x_span:
            return

        # Getting the indices of the 6 Heartbeats in the center of the screen
        center_indices = sort(
            (visible_range[self.x_axis_label.get()] - center).abs().sort_values()[:10].index.values)
        rri = visible_range.loc[center_indices][time_col].diff()
        rri.index = visible_range.loc[center_indices][self.x_axis_label.get()].values

        # Where to plot the lines and texts (After a certain threshold is plotted above)
        condition = ((self.data_handler[self.x_axis_label.get()] >= xlim_padded[0]) &
                     (self.data_handler[self.x_axis_label.get()] <= xlim_padded[1]))

        local_min = self.data_handler[self.y_axis_label.get()].loc[condition].min()
        y_pos_lines = local_min * 1.2
        y_pos_text = y_pos_lines - y_span * 0.03

        if y_pos_lines <= ylim[0] + 0.2 * y_span:
            local_max = self.data_handler[self.y_axis_label.get()].loc[condition].max()
            y_pos_lines = local_max * 1.2
            y_pos_text = y_pos_lines + y_span * 0.01

        offset = x_span * 0.005
        x_start = rri.index.values[:-1] + offset
        x_end = rri.index.values[1:] - offset
        self.graph_handler.plot_hlines([y_pos_lines] * (len(rri) - 1),
                                       x_start,
                                       x_end,
                                       name=f'metrics_RRi_{num}', color='black', linewidth=0.5)
        # Plotting the texts
        for i in range(len(rri) - 1):
            self.graph_handler.plot_text(rri.index[i] + x_span * 0.01,
                                         y_pos_text,
                                         f'{rri.iloc[i + 1]:.2f}s',
                                         color='black',
                                         name=f'RR_{i}:{num} [s]', fontsize=8)

    def annotate(self, event: MouseEvent, label: str) -> None:
        """
        Method to handle the annotation of a datapoint.
        :param event: Mouse event that holds coordinates of the mouse
        :param label: String - the label to annotate
        :return:
        """
        column = self.y_axis_label.get()
        data_pair = self.data_handler.get_xy_pair(self.x_axis_label.get(), column)
        _, _, _, _, ar = get_axis_geometry(self.graph_handler.axes[self.graph_handler.master_axis])
        click_index = find_closest_point(data=data_pair,
                                         target=(event.xdata, event.ydata),
                                         snap_on_max=self.snap_on_max.get(),
                                         aspect_ratio=ar / 2)
        try:
            self.data_handler.toggle_selected_label(click_index, label)
        except KeyError as e:
            messagebox.showerror(title='Error', message=str(e))
            return

        self.changes = True
        if label in SEGMENT_DENOMINATORS:
            self.plot_segment_information(label)
        else:
            self.scatter_plot_label_information(label)
        legend_without_duplicate_labels(self.graph_handler.axes[self.graph_handler.master_axis])

        if self.center_last_selection.get() == 1:
            self.graph_handler.move_to(x_pos=data_pair[0][click_index])
        else:
            self.graph_handler.refresh()


# Testing the screen
if __name__ == '__main__':
    root = RootWindow('Interval Viewer')
    data = DataHandler()
    data.in_app = True
    file = (r"C:\Users\gutge\OneDrive\Documents\Personal Documents\01_Education\02_Uni Basel - MSc Biomedical "
            r"Engineering\02_Curriculum\04_MSc Thesis\02_Data\03_Fully Annotated\Case_07_ECG.csv")
    data.open_file_no_gui(file)
    app = IntervalScreen(root, data)
    app.load_project()
    root.mainloop()
