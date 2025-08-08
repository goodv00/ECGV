"""
Class to create the main screen of this app

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-------------------------------------------
from tkinter import Tk, Frame, BOTH, messagebox, StringVar, IntVar, Label
from tkinter.ttk import Notebook
from matplotlib.backend_bases import MouseEvent
from numpy import sort, array

# Import functions from other scripts-----------------------
from modules.pop_ups import InputBox
from modules.data_handler import DataHandler
from modules.menu_bar import MenuBar
from modules.special_variables import SelectedLabel, YAxis, XAxis
from utils.helpers import find_closest_point, get_default_annotations
from modules.gui_elements import ThemedCheckbutton, ThemedButton, ThemedOptions
from modules.graph_handler import get_axis_geometry, legend_without_duplicate_labels
from screens.paned_screen_templates import TwoPanelTemplate
from analysis.ecg_toolbox import frequency_filtering_butterworth

# Global variables------------------------------------------
OPTION_BUTTON_ALIGNMENT = {
    'Take Screenshot': {'column': 0, 'row': 0, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nsew'},
    'Backward': {'column': 0, 'row': 1, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
    'Forward': {'column': 1, 'row': 1, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
    'Start': {'column': 0, 'row': 2, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
    'End': {'column': 1, 'row': 2, 'columnspan': 1, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
    'Move to last': {'column': 0, 'row': 3, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
    'Zoom out': {'column': 0, 'row': 4, 'columnspan': 2, 'rowspan': 1, 'pady': 2, 'sticky': 'nesw'},
}
DEFAULT_HEARTBEAT_CLASSES = get_default_annotations()['heartbeat_classes']
SEGMENT_DENOMINATORS = get_default_annotations()['segment_denominators']
COLOR_PALETTE = get_default_annotations()['standard_colors']


# Static functions -----------------------------------------


# Classes---------------------------------------------------
class AnnotationScreen(TwoPanelTemplate):
    def __init__(self, screen_root: Tk | Notebook | Frame, app_data_handler: DataHandler) -> None:
        super().__init__(screen_root, app_data_handler)
        # Dummy variables
        self.tooltip = None
        self.label_selector = None
        self.label_browser_buttons = None
        self.changes = False
        self.move_to_boxes = None
        self.center_last_selection = IntVar()
        self.snap_on_max = IntVar()
        self.snap_on_max.set(1)
        self.show_labels = IntVar()
        self.show_labels.set(1)
        self.show_datapoints = IntVar()
        self.menu = None
        self.menu_bar_items = None
        self.y_axis_selector = None
        self.x_axis_selector = None
        self.on_screen_actions = None
        self.on_screen_options = None

        # Special variables
        self.selected_label = SelectedLabel(self.root, '', data_handler=self.data_handler)
        self.y_axis_label = YAxis(self.root, '', data_handler=self.data_handler)
        self.x_axis_label = XAxis(self.root, '', data_handler=self.data_handler)

        # Modifying the GraphHandler
        self.graph_handler.snap_on_max = self.snap_on_max
        self.graph_handler.injected_actions['left_select'] = self.left_click
        self.graph_handler.injected_actions['refresh'] = self.show_on_screen_metrics

        # Initialing the screen
        self.load_options_panel(['Options', 'Actions', 'Y-Axis',
                                 'X-Axis', 'Browse label', 'Selection label'])
        self.load_on_screen_options()
        self.load_on_screen_actions()
        self.load_on_screen_label_selector(self.selected_label)
        self.load_label_browser()
        self.load_on_screen_axis_selector()
        self.load_tooltips()

    """
    Methods to load screen items
    """

    def load_on_screen_actions(self):
        self.on_screen_actions = {
            'Take Screenshot': ThemedButton(self.options_panel_frames['Actions'], text='Take Screenshot'),
            'Backward': ThemedButton(self.options_panel_frames['Actions'], text='Backward'),
            'Forward': ThemedButton(self.options_panel_frames['Actions'], text='Forward'),
            'Start': ThemedButton(self.options_panel_frames['Actions'], text='Start'),
            'End': ThemedButton(self.options_panel_frames['Actions'], text='End'),
            'Move to last': ThemedButton(self.options_panel_frames['Actions'], text='Move to last label'),
            'Zoom out': ThemedButton(self.options_panel_frames['Actions'], text='Zoom out'),
        }

        action_variables = {
            'Take Screenshot': self.graph_handler.take_screenshot,
            'Backward': lambda: self.graph_handler.move_backward(),
            'Forward': lambda: self.graph_handler.move_forward(),
            'Start': lambda: self.graph_handler.move_to(
                x_pos=self.data_handler[self.data_handler.x_axis_header].loc[0]),
            'End': lambda: self.graph_handler.move_to(
                x_pos=self.data_handler[self.data_handler.x_axis_header].loc[len(self.data_handler) - 1]),
            'Move to last': lambda: self.graph_handler.move_to(self.data_handler.get_last_label_location()),
            'Zoom out': lambda: self.graph_handler.show_x_window(
                self.data_handler[self.data_handler.x_axis_header].loc[0],
                self.data_handler[self.data_handler.x_axis_header].loc[len(self.data_handler) - 1]),
        }

        # Required so the buttons scale with the panel after resizing
        self.options_panel_frames['Actions'].columnconfigure(0, weight=1)
        self.options_panel_frames['Actions'].columnconfigure(1, weight=1)

        for i, (key, value) in enumerate(self.on_screen_actions.items()):
            self.options_panel_frames['Actions'].rowconfigure(i, weight=1)
            value.grid(**OPTION_BUTTON_ALIGNMENT[key])
            value.configure(command=action_variables[key])

    def load_on_screen_options(self):
        self.on_screen_options = {
            'Snap': ThemedCheckbutton(self.options_panel_frames['Options'],
                                      text='Snap on local max'),
            'Center': ThemedCheckbutton(self.options_panel_frames['Options'],
                                        text='Center on selection'),
            'Show_Labels': ThemedCheckbutton(self.options_panel_frames['Options'],
                                             text='Show labels'),
            'Show_Datapoints': ThemedCheckbutton(self.options_panel_frames['Options'],
                                                 text='Show datapoints'),
        }
        options_variables = {
            'Snap': {'variable': self.snap_on_max},
            'Center': {'variable': self.center_last_selection},
            'Show_Labels': {'variable': self.show_labels, 'command': lambda: self.refresh_graph(keep_window=True)},
            'Show_Datapoints': {'variable': self.show_datapoints, 'command': lambda: self.refresh_graph(keep_window=True)},
        }

        for key, value in self.on_screen_options.items():
            value.pack(padx=5, pady=2, anchor='w', fill=BOTH)
            value.configure(**options_variables[key])

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

    def load_label_browser(self):

        self.label_browser_buttons = {
            'Backward': ThemedButton(self.options_panel_frames['Browse label'], text='<-'),
            'Forward': ThemedButton(self.options_panel_frames['Browse label'], text='->'),
        }

        action_variables = {
            'Backward': lambda: self.move_to_next_index(which='previous'),
            'Forward': lambda: self.move_to_next_index(),
        }
        self.options_panel_frames['Browse label'].columnconfigure(0, weight=1)
        self.options_panel_frames['Browse label'].columnconfigure(1, weight=1)

        for key, value in self.label_browser_buttons.items():
            value.grid(**OPTION_BUTTON_ALIGNMENT[key])
            value.configure(command=action_variables[key])

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

    # In-window functionality ---------------------------------
    def refresh_graph(self, keep_window=False) -> None:
        """
        Method used to refresh the on-screen graph. Will plot the main line-plots
        :return: None
        """

        # Cancel if there is no data to display
        if self.data_handler.plot_data is None:
            return

        if keep_window:
            xlim = self.graph_handler.axes[self.graph_handler.master_axis].get_xlim()
            ylim = self.graph_handler.axes[self.graph_handler.master_axis].get_ylim()

        x_column = self.x_axis_label.get()
        y_column = self.y_axis_label.get()
        args = (self.data_handler[x_column], self.data_handler[y_column])
        filtered_signal = frequency_filtering_butterworth(self.data_handler[y_column], 130, upper=40, lower=0.5)

        # Plotting the raw signal in line-plot
        kwargs = {'name': y_column, 'label': 'Raw signal', 'color': 'k', 'linewidth': 2}
        self.graph_handler.plot_line_plot(*args, **kwargs)

        if self.show_datapoints.get() == 1:
            # Plot all datapoints
            kwargs = {'name': 'Datapoints', 'label': 'Datapoints', 'color': 'gray', 'marker': '^'}
            self.graph_handler.plot_scatter_plot(*args, **kwargs)
        else:
            self.graph_handler.remove_all_scatters(name_filter='Datapoints')

        # Plotting a filtered signal in line-plot (BPF 0.5-40Hz)
        kwargs = {'name': 'filtered', 'label': 'Filtered 0.5Hz-40Hz', 'color': 'r', 'linewidth': 0.3}
        self.graph_handler.plot_line_plot(self.data_handler[x_column], filtered_signal, **kwargs)

        # Plotting all label information
        self.plot_all_label_information()

        # Setting axis names
        self.graph_handler.axes[self.graph_handler.master_axis].set_ylabel(y_column)
        self.graph_handler.axes[self.graph_handler.master_axis].set_xlabel(x_column.split(' [')[0])

        if keep_window:
            self.graph_handler.axes[self.graph_handler.master_axis].set_xlim(xlim)
            self.graph_handler.axes[self.graph_handler.master_axis].set_ylim(ylim)

        legend_without_duplicate_labels(self.graph_handler.axes[self.graph_handler.master_axis])
        self.graph_handler.refresh(zoom=True)

    def plot_all_label_information(self) -> None:
        """
        Method to plot all label information
        :return:
        """
        # Plotting the label information
        self.graph_handler.remove_all_scatters(name_filter='label_')
        self.graph_handler.remove_all_text(name_filter='segments_')
        self.graph_handler.remove_all_vlines(name_filter='segments_')
        self.graph_handler.remove_all_scatters(name_filter='segments_')

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

        if self.show_labels.get() == 0:
            return

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

        if self.show_labels.get() == 0:
            return

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

    def update_options(self) -> None:
        """
        Method to update all options when coming back to this tab. Must-have method
        :return: None
        """
        # Making sure the selected labels are same again
        self.selected_label.sync()
        self.load_on_screen_axis_selector()
        self.load_on_screen_label_selector(self.selected_label)

    def load_project(self) -> None:
        """
        Method to load a project onto the annotation screen
        :return:
        """
        self.graph_handler.reset(reset_window=True, reset_custom_labels=True)
        self.set_title(self.data_handler.filename)
        self.selected_label.set(self.data_handler.selected_label)
        self.y_axis_label.set(self.data_handler.y_axis_header)
        self.x_axis_label.set(self.data_handler.x_axis_header)
        self.select_x_axis(self.x_axis_label.get())
        self.update_options()
        self.refresh_graph()
        self.graph_handler.show_x_window(0, 10000, self.graph_handler.master_axis)

    def reload_project(self):
        """
        Method to reload the graph.
        :return:
        """
        if not messagebox.askokcancel(title='Warning', message='Reload graph? All changes will be lost...'):
            return
        self.data_handler.get_file()
        self.load_project()

    def create_label(self, label: str):
        """
        Method to create a new label
        :return:
        """
        try:
            self.data_handler.declare_label(label)
            self.selected_label.assign(label)
            self.load_on_screen_label_selector(self.selected_label)
        except ValueError as e:
            messagebox.showerror(title='Error', message=str(e))

    def set_delimiter(self):
        """
        Method to set the delimiter of the DataHandler
        :return:
        """
        InputBox(title='Set delimiter...', enter_action=self.data_handler.set_delimiter)

    # Selection functionality ------------------------------------------------------------
    def left_click(self, event: MouseEvent) -> None:
        """
        Method used when clicking left mouse button
        :param event:
        :return:
        """
        if self.data_handler.plot_data is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        label = self.selected_label.get()
        self.annotate(event, label)

    def annotate(self, event: MouseEvent, label: str) -> None:
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

    def move_to_next_index(self, which='next') -> None:
        """
        Method to move the graph to the next anomaly location, stored in self.anomalies
        :param which:
        :return:
        """
        if ((self.selected_label.get() == '') |
                (self.data_handler.plot_data is None) |
                (not bool(self.data_handler.label_list))):
            return

        x_axis = self.data_handler.get_label_data(self.selected_label.get())[self.x_axis_label.get()]
        location = self.graph_handler.master_location.get()
        if x_axis.empty:
            return
        match which:
            case 'next':
                next_locations = x_axis.loc[x_axis > location]
                if len(next_locations) == 0:
                    next_location = x_axis.iloc[0]
                else:
                    next_location = next_locations.iloc[0]
            case 'previous':
                next_locations = x_axis.loc[x_axis < location]
                if len(next_locations) == 0:
                    next_location = x_axis.iloc[-1]
                else:
                    next_location = next_locations.iloc[-1]
            case _:
                raise ValueError('Arguments "which" has to be either "next" or "previous"')

        self.graph_handler.move_to(next_location)

    def show_on_screen_metrics(self) -> None:
        """
        Method that plot pulse metrics when Heartbeats labels are present. The method will display the average HR in bpm
        over the visible range of labels, and it will show the RR intervals of several beats on screen when zoomed
        to a certain level.

        Sorry for the convoluted method...

        :return:
        """

        if (self.data_handler.plot_data is None) or not bool(self.data_handler.label_list):
            return

        heartbeat_segments = self.data_handler.get_heartbeats()
        time_col = 'sensor timer [s]'

        self.graph_handler.remove_all_text(name_filter='RR_')
        self.graph_handler.remove_all_text(name_filter='HR')
        self.graph_handler.remove_all_text(name_filter='Avg HR')
        self.graph_handler.remove_all_hlines(name_filter='metrics_')
        self.graph_handler.remove_all_vlines(name_filter='metrics_')

        if len(heartbeat_segments) == 0 or (time_col not in self.data_handler.plot_data.columns):
            return

        # Getting axis geometry
        x_span, y_span, x_loc, y_loc, ar = get_axis_geometry(self.graph_handler.axes[self.graph_handler.master_axis])
        ylim = self.graph_handler.axes[self.graph_handler.master_axis].get_ylim()
        xlim = self.graph_handler.axes[self.graph_handler.master_axis].get_xlim()
        xlim_padded = (array(xlim) + array([0.1, -0.1]) * x_span).astype(float)
        center = self.graph_handler.master_location.get()

        for num, heartbeats in enumerate(heartbeat_segments):
            # Computing on-screen metrics
            condition = ((heartbeats[self.x_axis_label.get()] >= xlim_padded[0]) &
                         (heartbeats[self.x_axis_label.get()] <= xlim_padded[1]))
            visible_range = heartbeats.loc[condition]

            # Stop if no on-screen labels
            if len(visible_range) <= 1:
                continue
            # Stop if the current segment is too short to see on screen
            if visible_range[self.x_axis_label.get()].diff().sum() <= 0.1 * x_span:
                continue

            avg_hr = (60 / visible_range[time_col].diff()).mean()
            # Plotting the heart rate spanner at the bottom of the screen
            y_pos = ylim[0] + y_span * 0.05
            x_pos = visible_range[self.x_axis_label.get()].values[[0, -1]]
            args = (y_pos, *x_pos)
            kwargs = {'name': f'metrics_Avg HR_{num}', 'color': 'grey', 'linestyle': 'dotted'}
            self.graph_handler.plot_hlines(*args, **kwargs)  # This is the dashed horizontal line

            offset = y_span * 0.01
            args = (x_pos, y_pos - offset, y_pos + offset)
            kwargs = {'name': f'metrics_borders_{num}', 'color': 'grey', 'linestyle': 'dotted'}
            self.graph_handler.plot_vlines(*args, **kwargs)  # This is the vertical line
            # Finally plotting the text
            y_pos = y_pos + y_span * 0.01
            x_pos = x_pos[0] + 0.005 * x_span
            self.graph_handler.plot_text(x_pos, y_pos, f'{avg_hr:.0f}bpm', name=f'Avg HR_{num}', fontsize=8)

            # If zoomed in adequately, RRi metrics will be displayed
            if visible_range[self.x_axis_label.get()].diff().mean() <= 0.05 * x_span:
                continue

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
                                           name=f'metrics_RRi_{num}', color='black', linewidth=0.5, linestyle='dotted')
            # Plotting the texts
            for i in range(len(rri) - 1):
                self.graph_handler.plot_text(rri.index[i] + x_span * 0.01,
                                             y_pos_text,
                                             f'{rri.iloc[i + 1]:.2f}s',
                                             color='black',
                                             name=f'RR_{i}:{num} [s]', fontsize=8)

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

    # Functionality (if called standalone) ------------------------------------------------
    def load_menu_bar(self):
        # Configuring the main menu
        self.menu_bar_items = {
            'File': {
                'Open...': self.open_file_sequence,
                'Save...': self.data_handler.save_file,
                'Save as...': self.data_handler.save_file_as,
                'Separator_1': None,
                'Reload project': self.reload_project,
                'Separator_2': None,
                'Exit': self.root.destroy,
            },
            'Edit': {
                'Create Label': lambda: InputBox(title='Define new label', enter_action=self.create_label),
                'Separator': None,
                'Set file delimiter': self.set_delimiter,
            }
        }
        self.menu = MenuBar(self.root, self.menu_bar_items)

    def open_file_sequence(self) -> None:
        """
        Method to open a file dialog to select a file and plot it on the main graph.
        :return: None
        """
        if self.data_handler.plot_data is not None:
            response = messagebox.askokcancel('Load Project...',
                                              'Loading the project will delete all unsaved changes. Continue?')
            if not response:
                return
        self.data_handler.get_and_open_file()
        self.load_project()

    """
    Tooltips
    """

    def load_tooltips(self) -> None:
        # Create a tooltip label (initially hidden)
        self.tooltip = Label(self.root, text="", bg="#DEE6E8", fg="black", relief="solid", borderwidth=1)
        self.tooltip.place_forget()

        # Bind hover events to the button
        self.options_panel_frames['Browse label'].bind("<Enter>", self.show_tooltip)
        self.options_panel_frames['Browse label'].bind("<Leave>", lambda _: self.hide_tooltip())

    def show_tooltip(self, event):
        self.tooltip.place(x=event.x_root - self.root.winfo_rootx() + 10,
                           y=event.y_root - self.root.winfo_rooty() + 10)
        self.tooltip.config(text="Select a label and browse through its members!")

    def hide_tooltip(self):
        self.tooltip.place_forget()


if __name__ == '__main__':
    root = Tk()
    data = DataHandler()
    data.in_app = True
    app = AnnotationScreen(root, data)
    app.load_menu_bar()
    root.mainloop()
