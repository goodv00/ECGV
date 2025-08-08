"""
Plot handler class. Takes care of data plot in-app.

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages ------------------------------------------
import os
from math import prod
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure, Axes
from matplotlib.lines import Line2D
from matplotlib.collections import PathCollection
from numpy import array, where, ndarray, full, float16, float32, float64, int8, int16, int32
from matplotlib.colors import TABLEAU_COLORS
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator, FuncFormatter, ScalarFormatter, AutoLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backend_bases import MouseEvent, KeyEvent
from matplotlib.patches import Rectangle
from tkinter import PanedWindow, LabelFrame, BOTH, Tk, IntVar, filedialog, Event, Frame, DoubleVar

# Import functions from other scripts ----------------------
from modules.data_handler import DataHandler
from utils.helpers import find_closest_point, all_type_x
from modules.master_slider import MasterSlider

# Global variables -----------------------------------------
matplotlib.pyplot.style.use(['fast'])
matplotlib.rc_context({'lines.linewidth': 1})
matplotlib.rcParams['agg.path.chunksize'] = 2000
matplotlib.rcParams['path.simplify'] = True
matplotlib.rcParams['path.simplify_threshold'] = 0.5
matplotlib.rcParams['font.size'] = 11
matplotlib.rcParams['lines.linewidth'] = 0.5
COLORS = list(TABLEAU_COLORS.values())

dragging = False
hide_tick = True


# Static functions -----------------------------------------
def legend_without_duplicate_labels(ax: Axes) -> None:
    """
    Display matplotlib legend without duplicates.
    Line plots appear first, scatter plots last.
    :param ax: The matplotlib axes object which shall feature the legend
    """
    handles, labels = ax.get_legend_handles_labels()

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for h, l in zip(handles, labels):
        if l not in seen:
            seen.add(l)
            unique.append((h, l))

    # Sort: Line2D first, others in middle, PathCollection last
    def sort_key(item):
        handle, _ = item
        if isinstance(handle, Line2D):
            return 0
        elif isinstance(handle, PathCollection):
            return 2
        else:
            return 1  # For any other types (e.g., bars, patches)

    unique_sorted = sorted(unique, key=sort_key)

    if unique_sorted:
        ax.legend(*zip(*unique_sorted), loc='upper right', facecolor='white')


def convert_to_hour_string(value: float | int) -> str:
    """
    Converse a series of numerical data which represents time in seconds to a series of strings of form:
    -> 'hh.hh'
    :param value:
    :return:
    """
    global hide_tick
    if hide_tick:
        hide_tick = False
        return ''
    hide_tick = True

    if value < 0:
        return ''
    return f'{int(value / 3600) % 3600:02d}.{int(((value / 3600) % 1) * 100):02d}h'


def convert_to_minute_string(value: float | int) -> str:
    """
    Converse a series of numerical data which represents time in seconds to a series of strings of form:
    -> mm.mm
    :param value:
    :return:
    """

    global hide_tick
    if hide_tick:
        hide_tick = False
        return ''
    hide_tick = True

    if value < 0:
        return ''
    if value >= 3600:
        return f'{int(value / 3600):02d}:{int(value / 60) % 60:02d}.{int(((value / 60) % 1) * 100):02d}m'
    else:
        return f'{int(value / 60) % 60:02d}.{int(((value / 60) % 1) * 100):02d}m'


def convert_to_seconds_string(value: float | int) -> str:
    """
    Converse a series of numerical data which represents time in seconds to a series of strings of form:
    -> ss.ss
    :param value:
    :return:
    """

    global hide_tick
    if hide_tick:
        hide_tick = False
        return ''
    hide_tick = True

    if value < 0:
        return ''
    if value >= 3600:
        time_string = f'{int(value / 3600):02d}:{int(value / 60) % 60:02d}:{int(value % 60):02d}s'
    elif value >= 60:
        time_string = f'{int(value / 60) % 60:02d}:{int(value % 60):02d}s'
    else:
        time_string = f'{int(value % 60):02d}s'

    return time_string.replace('s', '') + f'.{int(10 * (round(value % 1, 1))):01d}s'


def get_axis_geometry(ax: Axes) -> tuple:
    """
    Method to get the geometry of an axes
    :return: Span, location and aspect ratio of the current axis
    """
    x_lim = ax.get_xlim()
    x_span = abs(x_lim[1] - x_lim[0])
    x_loc = x_lim[0] + x_span / 2
    y_lim = ax.get_ylim()
    y_span = abs(y_lim[1] - y_lim[0])
    y_loc = y_lim[0] + y_span / 2
    ar = x_span / y_span

    return x_span, y_span, x_loc, y_loc, ar


# Classes --------------------------------------------------
class GraphHandler:
    """
    GraphHandler class takes care of in-app matplotlib graph. It creates a matplotlib figure within a tkinter widget
    and offers several methods for dynamic and interactive graphs. It is possible to use a single axis, subplots or even
    GridSpec (for more information check Matplotlib documentation).
    """

    def __init__(self, container: PanedWindow | Tk | LabelFrame | Frame, **kwargs):
        self.hover_coord = None
        self.master_axis = (0, 0)
        self.kwargs: any = kwargs
        self.x_bins: list | None = None
        self.x_customized: bool = False
        self.x_labels_and_ticks: tuple[list, list] | None = None
        self.y_bins = None
        self.y_customized = False
        self.y_labels_and_ticks = None
        self.axis_pointer = (0, 0)
        self.click_event = None
        self.master_slider = None
        self.master_location = DoubleVar()
        self.data_length = None
        self.key_pressed = None
        self.aspect_ratio = None
        self.graph_height = None
        self.graph_width = None
        self.hover_point = None  # Matplotlib object (single scatter plot)
        self.key_actions_on_master_only = False
        self.snap_on_max = IntVar()
        self.screenshot_folder = None

        self.lines = dict()
        """
        Line plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all scatter plots in a given plot... same label same index,
                    -'al_pairs'*: dict - shows on which axes the line plot label is active
                    -'color': color value of the scatter plot
                    }
        *axes_line_pairs are dicts of shape {'ax': matplotlib.collections.PathCollection,}
        """

        self.scatter_plots = dict()
        """
        Scatter plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all scatter plots in a given plot... same label same index,
                    -'as_pairs'*: dict - shows on which axes the scatter plot label is active
                    -'color': color value of the scatter plot
                    }
        *axes_scatter_pairs are dicts of shape {'ax': matplotlib.collections.PathCollection,}
        """

        self.vlines = dict()
        """
        vline plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all vline plots in a given plot... same label same index,
                    -'av_pairs'*: dict - shows on which axes the vline plot label is active
                    -'color': color value of the vline plot
                    -'kwargs': kwargs passed for this vline label
                    }
        *axes_vline_pairs are dicts of shape {'ax': matplotlib.collections.LineCollection,}
        """

        self.hlines = dict()
        """
        hline plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all vline plots in a given plot... same label same index,
                    -'ah_pairs'*: dict - shows on which axes the hline plot label is active
                    -'color': color value of the hline plot
                    -'kwargs': kwargs passed for this hline label
                    }
        *axes_hline_pairs are dicts of shape {'ax': matplotlib.collections.LineCollection,}
        """

        self.texts = dict()
        """
        text plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all vline plots in a given plot... same label same index,
                    -'at_pairs'*: dict - shows on which axes the text plot label is active
                    -'kwargs': kwargs passed for this hline label
                    }
        *axes_hline_pairs are dicts of shape {'ax': matplotlib.collections.LineCollection,}
        """

        self.boxes = dict()
        """
        box plot management in dict form.
        Contains key: value pairs of:
        -'label':   dict - contains elements:{
                    -'index': int - enumerate all vline plots in a given plot... same label same index,
                    -'ab_pairs'*: dict - shows on which axes the text plot label is active
                    -'kwargs': kwargs passed for this hline label
                    }
        *axes_hline_pairs are dicts of shape {'ax': matplotlib.collections.LineCollection,}
        """

        self.injected_actions = {
            'left_select': lambda *args: print('left'),
            'right_select': lambda *args: print('right'),
            'middle_select': lambda *args: print('middle'),
            'hover': lambda *args: self.default_hover_function(*args),
            'move': lambda *args: None,
            'zoom': lambda *args: None,
            'refresh': lambda *args: None,
            'key_pressed': lambda *args: None,
        }

        self.sharex: bool | list | None = None
        self.sharey: bool | list | None = None
        self.root = container
        self.data_directory = None
        self.axes = None
        self.figure = None
        self.canvas = None
        self.create_figure(**kwargs)

    def reset(self, reset_window=True, reset_custom_labels=False, hard=False) -> None:
        """
        Resets user inputs of the handler
        :return: None
        """
        if self.axes is not None:
            for ax in self.axes.flatten():
                if ax is None:
                    continue
                ax.clear()

        if reset_window or hard:
            self.aspect_ratio = None
            self.graph_height = None
            self.graph_width = None

        if reset_custom_labels or hard:
            self.x_bins = None
            self.x_customized = False
            self.x_labels_and_ticks = None
            self.y_bins = None
            self.y_customized = False
            self.y_labels_and_ticks = None

        if hard:
            self.data_length = None
            self.figure.clear()
            self.sharex = None
            self.sharey = None
            self.data_directory = None
            self.axes = None
            self.screenshot_folder = None

        self.axis_pointer = (0, 0)
        self.hover_coord = None
        self.click_event = None
        self.key_pressed = None
        self.hover_point = None  # Matplotlib object (single scatter plot)
        self.scatter_plots = dict()
        self.vlines = dict()
        self.hlines = dict()
        self.texts = dict()
        self.lines = dict()
        self.boxes = dict()

    def remove_hover(self) -> None:
        """
        Removes the hover point on the graph
        :return: None
        """
        if self.hover_point is not None:
            self.hover_point.remove()
            self.hover_point = None
            self.hover_coord = None
        if self.click_event is not None:
            self.click_event = None

    def refresh(self, zoom: bool = False) -> None:
        """
        Refreshes the graph. This method is essential to updating the plot to any changes
        :param zoom: bool - if True, slider and ticks will be reloaded to adjust to new window
        :return: None
        """
        if self.axes is None:
            return
        _, _, x_loc, _, _ = get_axis_geometry(self.axes[self.master_axis])
        self.master_location.set(x_loc)
        self.injected_actions['refresh']()
        if zoom:
            self.initiate_slider()
            self.update_x_ticks(self.axis_pointer)
        self.canvas.draw_idle()

        # Otherwise there could be a weird toggling of the values
        global hide_tick
        hide_tick = False

    """
    Plot functions
    The below methods create the content of the graph
    """

    def plot_line_plot(self, *args, name: str,
                       axis_selector: tuple[int, int] = (0, 0),
                       slider: bool = True, **kwargs) -> None:
        """
        Method to plot a line plot
        :param args: args passed for to matplotlib.pyplot.plot
        :param name: string - Name of the plot item. Used as identifier in lines dict
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param slider: bool - If true, will update the slider according to length of the plot data
        :param kwargs: kwargs passed to matplotlib.pyplot.plot
        :return: None
        """
        ax = str(axis_selector)

        if name not in self.lines:
            self.lines[name] = {'al_pairs': {}}
            self.lines[name]['index'] = len(self.lines)
            if name in self.scatter_plots:
                kwargs['color'] = self.scatter_plots[name]['color']
            elif 'color' not in kwargs:
                kwargs['color'] = COLORS[len(self.lines) % len(COLORS)]
        elif name in self.lines:
            kwargs['color'] = self.lines[name]['kwargs']['color']
            if ax in self.lines[name]['al_pairs']:
                for item in self.lines[name]['al_pairs'][ax]:
                    item.remove()

        # Making the entry into the lines dict
        self.lines[name]['kwargs'] = kwargs
        self.lines[name]['al_pairs'][ax] = self.axes[axis_selector].plot(*args, **kwargs)

        if slider:
            self.data_length = max(args[0])

    def plot_scatter_plot(self, *args, name: str,
                          axis_selector: tuple[int, int] = (0, 0),
                          **kwargs) -> None:
        """
        Method to plot a scatter plot
        :param args: args passed to matplotlib.pyplot.scatter
        :param name: string - label of the scatter data
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param kwargs: keyword arguments that go into plt.scatter. 
                        Beware, I'll overwrite color so each scatter has a unique color
        :return: None
        """
        ax = str(axis_selector)
        if name not in self.scatter_plots:
            self.scatter_plots[name] = {'as_pairs': {}}
            self.scatter_plots[name]['index'] = len(self.scatter_plots)
            if 'color' not in kwargs:
                kwargs['color'] = COLORS[self.scatter_plots[name]['index'] % len(COLORS)]
        elif ax in self.scatter_plots[name]['as_pairs']:
            self.scatter_plots[name]['as_pairs'][ax].remove()
            if 'color' not in kwargs:
                kwargs['color'] = self.scatter_plots[name]['color']
        else:
            if 'color' not in kwargs:
                kwargs['color'] = self.scatter_plots[name]['color']

        # Making the entry into the scatter plot dict
        args = (args[0], args[1])
        self.scatter_plots[name]['as_pairs'][ax] = self.axes[axis_selector].scatter(*args, **kwargs)
        self.scatter_plots[name]['color'] = kwargs['color']
        legend_without_duplicate_labels(self.axes[axis_selector])

    def plot_vlines(self, *args, name: str, axis_selector: tuple[int, int] = (0, 0), **kwargs) -> None:
        """
        Method to plot vertical lines
        :param args - x_locations (array like of ints) of vlines, y-min and y-max (floats) indicate length of vlines
        :param name: string - label of the scatter data
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param kwargs: kwargs pass to matplotlib.pyplot.vlines.
        :return:
        """
        ax = str(axis_selector)

        if name not in self.vlines:
            self.vlines[name] = {'av_pairs': {}}
            self.vlines[name]['index'] = len(self.vlines)
            if name in self.scatter_plots:
                kwargs['color'] = self.scatter_plots[name]['color']
            elif 'color' not in kwargs:
                kwargs['color'] = COLORS[len(self.vlines) % len(COLORS)]
        elif name in self.vlines:
            kwargs['color'] = self.vlines[name]['kwargs']['color']
            if ax in self.vlines[name]['av_pairs']:
                self.vlines[name]['av_pairs'][ax].remove()

        # Making the entry into the vlines dict
        self.vlines[name]['kwargs'] = kwargs
        self.vlines[name]['av_pairs'][ax] = self.axes[axis_selector].vlines(*args, **kwargs)

    def plot_hlines(self, *args, name: str, axis_selector: tuple[int, int] = (0, 0), **kwargs) -> None:
        """
        Method to plot horizontal lines. Super slow method, do not used in app if you don't want lag
        :param args - x_locations (array like of ints) of vlines, y-min and y-max (floats) indicate length of hlines
        :param name: string - label of the scatter data
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param kwargs: kwargs pass to matplotlib.pyplot.hlines.
        :return: None
        """
        ax = str(axis_selector)

        if name not in self.hlines:
            self.hlines[name] = {'ah_pairs': {}}
            self.hlines[name]['index'] = len(self.hlines)
            if 'color' not in kwargs:
                kwargs['color'] = COLORS[len(self.hlines) % len(COLORS)]
        elif name in self.hlines:
            kwargs['color'] = self.hlines[name]['kwargs']['color']
            if ax in self.hlines[name]['ah_pairs']:
                self.hlines[name]['ah_pairs'][ax].remove()

        # Making the entry into the hlines dict
        self.hlines[name]['kwargs'] = kwargs
        self.hlines[name]['ah_pairs'][ax] = self.axes[axis_selector].hlines(*args, **kwargs)

    def plot_text(self, *args, name: str, axis_selector: tuple[int, int] = (0, 0), **kwargs) -> None:
        """
        Method to plot text.
        :param args: args passed to matplotlib.pyplot.text.
        :param name: string - label of the scatter data
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param kwargs: kwargs passed to matplotlib.pyplot.text.
        :return: None
        """
        ax = str(axis_selector)

        if name not in self.texts:
            self.texts[name] = {'at_pairs': {}}
            self.texts[name]['index'] = len(self.texts)
        elif name in self.texts:
            if ax in self.texts[name]['at_pairs']:
                self.texts[name]['at_pairs'][ax].remove()

        # Making the entry into the texts dict
        self.texts[name]['kwargs'] = kwargs
        self.texts[name]['at_pairs'][ax] = self.axes[axis_selector].text(*args, **kwargs)

    def plot_box(self, *args, name: str, axis_selector: tuple[int, int] = (0, 0), **kwargs) -> None:
        """
        Method to plot text.
        :param args: args passed to matplotlib.patched.Rectangle
        :param name: string - label of the scatter data
        :param axis_selector: tuple - selector to select matplotlib.axes.Axes object from self.axes
        :param kwargs: kwargs passed to matplotlib.patched.Rectangle
        :return:
        """
        ax = str(axis_selector)

        if name not in self.boxes:
            self.boxes[name] = {'at_pairs': {}}
            self.boxes[name]['index'] = len(self.texts)
        elif name in self.boxes:
            if ax in self.boxes[name]['at_pairs']:
                self.boxes[name]['at_pairs'][ax].remove()

        # Making the entry into the texts dict
        self.boxes[name]['kwargs'] = kwargs
        self.boxes[name]['at_pairs'][ax] = Rectangle(*args, **kwargs)
        self.axes[axis_selector].add_patch(self.boxes[name]['at_pairs'][ax])

    def plot_hover_point(self, *args, **kwargs) -> None:
        """
        Method to plot a single point as a scatter plot. See
        :param args: args passed to matplotlib.pyplot.scatter.
        :param kwargs: kwargs passed to matplotlib.pyplot.scatter.
        :return: None
        """
        if 'color' not in kwargs:
            kwargs['color'] = 'k'
        if 'marker' not in kwargs:
            kwargs['marker'] = 'x'
        if self.hover_point is not None:
            self.hover_point.remove()
        self.hover_point = self.axes[self.axis_pointer].scatter(*args, **kwargs)

    """
    Removal functions
    Functions to remove scatters and lines or text
    """

    def remove_all_lines(self, name_filter: str | None = None, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all line plots stored in self.lines
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.lines):
            return

        for name, value in self.lines.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['al_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    for item in value['al_pairs'][ax]:
                        item.remove()
                else:
                    continue
            self.lines.pop(name)

    def remove_all_scatters(self, name_filter: str | None = None,
                            axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all scatter plots
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.scatter_plots):
            return

        for name, value in self.scatter_plots.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['as_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    value['as_pairs'][ax].remove()
                else:
                    continue
            self.scatter_plots.pop(name)

    def remove_all_vlines(self, name_filter: str | None = None, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all vline plots
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.vlines):
            return

        for name, value in self.vlines.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['av_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    value['av_pairs'][ax].remove()
                else:
                    continue
            self.vlines.pop(name)

    def remove_all_hlines(self, name_filter: str | None = None, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all hline plots
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.hlines):
            return

        for name, value in self.hlines.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['ah_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    value['ah_pairs'][ax].remove()
                else:
                    continue
            self.hlines.pop(name)

    def remove_all_text(self, name_filter: str | None = None, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all text plots
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.texts):
            return

        for name, value in self.texts.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['at_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    value['at_pairs'][ax].remove()
                else:
                    continue
            self.texts.pop(name)

    def remove_all_boxes(self, name_filter: str | None = None, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Removes all text plots
        :param axis_selector: tuple - used to delete a specific axis items only
        :param name_filter: string or None - if given will search for this string in name of self.lines objects
        :return: None
        """
        if not bool(self.boxes):
            return

        for name, value in self.boxes.copy().items():
            if (name_filter is not None) and (name_filter not in name):
                continue
            for ax in value['at_pairs']:
                if (axis_selector is None) or (ax == str(axis_selector)):
                    value['at_pairs'][ax].remove()
                else:
                    continue
            self.boxes.pop(name)

    """
    Action functions
    The below methods are actions for the graph
    """

    def take_screenshot(self, default_filename: str | None = None) -> None:
        """
        Method to save the current view in a folder
        :param default_filename: string - default name for file to save screenshot
        :return: None
        """
        directory = self.data_directory

        if default_filename is None:
            """
            Check location for screenshots
            """
            default_filename = "screenshot"

            items = os.listdir(directory)
            items_no_extension = [item.split(".")[0] for item in items]
            num = 1
            for item in items_no_extension:
                if item == default_filename + f'{num:02d}':
                    num += 1
                else:
                    continue
            default_filename += f'{num:02d}'

        # Get the desired filename form the user
        save_filename = filedialog.asksaveasfilename(title='Save Screenshot',
                                                     filetypes=[("PNG files", "*.png*"),
                                                                ("PDF files", "*.pdf*"),
                                                                ("SVG files", "*.svg*")],
                                                     initialfile=default_filename,
                                                     defaultextension='.png',
                                                     initialdir=directory)
        if save_filename == '':
            # Throw an error
            raise ValueError('No file was declared for saving')
        self.data_directory = os.path.dirname(save_filename)
        # Save the file as csv
        self.figure.savefig(save_filename)

    def highlight_axis(self, axis_selector: tuple[int, int] | None = None) -> None:
        """
        Method to change the background color of an axis to highlight where the axis pointer currently points at
        :param axis_selector: Tuple. Which axis to highlight
        :return: None
        """
        for ax in self.axes.flatten():
            if ax is None:
                continue
            ax.set_facecolor('white')
        # If selector is still None after assignment (other way to check for OR condition)
        if axis_selector is None:
            axis_selector = self.axis_pointer
        if axis_selector is None:
            return
        self.axes[axis_selector].set_facecolor('xkcd:off white')
        self.refresh()

    def zoom(self, x_delta: float = 0, y_delta: float = 0,
             axis_selector: tuple[int, int] | None = None,
             center: tuple[float, float] | None = None) -> None:
        """
        Method used when user zooms with two fingers on touchscreen
        :param center: xy pair of floats - center of zooming action
        :param axis_selector: tuple - selector to select matplotlin.Axes object from self.axes
        :param y_delta: float - how much to zoom on y
        :param x_delta: float - how much to zoom on x
        :return: None
        """
        if axis_selector is None:
            axis_selector = self.axis_pointer
        ax = self.axes[axis_selector]
        x_span, y_span, _, _, _ = get_axis_geometry(ax)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        if center is None:
            x_zoom = [0, x_delta]
            y_zoom = [0, y_delta]
        else:
            if center[0] is not None:
                a = center[0] - xlim[0]
                b = xlim[1] - center[0]

                dx1 = x_delta
                dx0 = a - (a/b) * (b - dx1)
                x_zoom = [dx0, -dx1]
            else:
                x_zoom = [0, x_delta]
            if center[1] is not None:
                a = center[1] - ylim[0]
                b = ylim[1] - center[1]

                dy1 = y_delta
                dy0 = a - (a / b) * (b - dy1)
                y_zoom = [dy0, -dy1]
            else:
                y_zoom = [0, y_delta]
        ax.set_xlim(array(xlim) + x_zoom)
        ax.set_ylim(array(ylim) + y_zoom)
        self.injected_actions['zoom']()
        self.refresh(zoom=True)

    def move_by(self, x_delta: float, y_delta: float,
                axis_selector: tuple[int, int] | None = None, refresh: bool = True) -> None:
        """
        Method that defines action when user drags the graph
        :param axis_selector: tuple - selector to select matplotlin.Axes object from self.axes
        :param x_delta: Distance by which to move the x-axis
        :param y_delta: Distance by which to move the y-axis
        :param refresh: If true, auto-refresh (do not use outside of graph handler, will create loop)
        :return:
        """
        if axis_selector is None:
            axis_selector = self.axis_pointer
        self.axes[axis_selector].set_xlim(array(self.axes[axis_selector].get_xlim()) + x_delta)
        self.axes[axis_selector].set_ylim(array(self.axes[axis_selector].get_ylim()) + y_delta)
        if refresh:
            self.injected_actions['move']()
            self.refresh()

    def move_to(self, x_pos: float | None = None, y_pos: float | None = None,
                axis_selector: tuple[int, int] | None = None, refresh: bool = True) -> None:
        """
        Method to move plot to a specific point
        :param axis_selector: tuple - selector to select matplotlin.Axes object from self.axes
        :param x_pos: Location on the x_axis
        :param y_pos: location on the y_axis
        :param refresh: If true, auto-refresh (do not use outside of graph handler, will create loop)
        :return:
        """
        if self.axis_pointer is None and axis_selector is None:
            return
        elif axis_selector is None:
            axis_selector = self.axis_pointer

        x_span, y_span, _, _, _ = get_axis_geometry(self.axes[axis_selector])

        if x_pos is not None:
            x_half = x_span / 2
            self.axes[axis_selector].set_xlim(array([-x_half, x_half]) + float(x_pos))
        if y_pos is not None:
            y_half = y_span / 2
            self.axes[axis_selector].set_ylim(array([-y_half, y_half]) + float(y_pos))
        if refresh:
            self.injected_actions['move']()
            self.refresh()

    def show_x_window(self, start: int | float, end: int | float,
                      axis_selector: tuple[int, int] | None = None, refresh=True) -> None:
        """
        Method to display a window with a fixed range of the x_axis. Uses plt.set_xlim
        :param refresh: If true - will call self.refresh to render changes
        :param start: Start of the window - int of float
        :param end: End of the window - int of float
        :param axis_selector: Tuple that defines which axis to operate on
        :return:
        """
        if axis_selector is None:
            axis_selector = self.axis_pointer
        self.axes[axis_selector].set_xlim(start, end)
        if refresh:
            self.refresh(zoom=True)

    """
    User interactions
    Methods to handle user inputs
    """

    def on_axis_enter(self, event: MouseEvent | Event) -> None:
        """
        Method to set the pointer to the axis where the mouse is pointing
        :param event: matplotlib.backend_bases.MouseEvent - holds in-graph information
        :return: None
        """
        # numpy.where will return a tuple with two arrays inside (don't ask me why)
        self.axis_pointer = tuple([int(i[0]) for i in where(event.inaxes == self.axes)])
        self.highlight_axis()

    def on_axis_leave(self) -> None:
        """
        Method to reset the axis color and pointer when the mouse leaves the figure
        :return: None
        """
        self.axis_pointer = self.master_axis
        self.click_event = None
        self.remove_hover()

    def on_mouse_motion(self, event: MouseEvent | Event) -> None:
        """
        Method to set the hover event and handle any dragging if needed
        :param event: Mouse event that holds mouse coordinates on the graph
        :return: None
        """
        global dragging
        if self.axis_pointer is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        if not dragging:
            self.injected_actions['hover'](event)
        if self.click_event is None:
            return
        if (self.click_event.xdata == event.xdata) and (self.click_event.ydata == event.ydata):
            return
        self.on_drag(event)

    def on_drag(self, event: MouseEvent | Event) -> None:
        """
        Method to handle different mouse click events
        :param event: Mouse event that holds mouse coordinates on the graph
        :return: None
        """
        global dragging
        dragging = True
        if event.xdata is None or event.ydata is None:
            return
        elif self.click_event is None:
            return
        elif self.click_event.xdata is None or self.click_event.ydata is None:
            return
        elif self.click_event.button == 1:
            self.move_by(self.click_event.xdata - event.xdata, self.click_event.ydata - event.ydata)
        elif self.click_event.button == 3:
            self.zoom(self.click_event.xdata - event.xdata, self.click_event.ydata - event.ydata)

    def on_click(self, event: MouseEvent | Event) -> None:
        """
        Method to handle when mouse button is clicked
        :param event: Mouse event
        :return: None
        """
        self.click_event = event
        global dragging
        dragging = False

    def on_release(self, event: MouseEvent | Event) -> None:
        """
        Method to handle when mouse button is released. This function is a little more complex as I distinguish
        between clicks and drags. So it checks if while the mouse button was clicked (see on_click) the mouse moved
        if that is the case, the method assumes that there was a drag motion and will not trigger the selection action
        :param event: matplotlib.backend_bases.MouseEvent
        :return: None
        """
        global dragging
        if dragging:
            dragging = False
            self.click_event = None
            return
        if self.click_event is None:
            dragging = False
            return
        if self.click_event.button == 1:
            self.injected_actions['left_select'](event)
        elif self.click_event.button == 3:
            self.injected_actions['right_select'](event)
        elif self.click_event.button == 2:
            self.injected_actions['middle_select'](event)
        self.click_event = None

    def on_key_press(self, event: KeyEvent | Event) -> None:
        """
        Method to handle all types of keyboard inputs
        :param event: matplotlib.backend_bases.KeyEvent - holds information on which key was pressed
        :return: None
        """
        if self.key_actions_on_master_only:
            ax = self.master_axis
        else:
            ax = self.axis_pointer
        self.key_pressed = event.key
        x_span, y_span, x_loc, y_loc, ar = get_axis_geometry(self.axes[ax])
        match self.key_pressed:
            case 'left':
                self.move_by(x_delta=-x_span / 5, y_delta=0, axis_selector=ax)
            case 'right':
                self.move_by(x_delta=x_span / 5, y_delta=0, axis_selector=ax)
            case 'up':
                self.move_by(x_delta=0, y_delta=-y_span / 5, axis_selector=ax)
            case 'down':
                self.move_by(x_delta=0, y_delta=y_span / 5, axis_selector=ax)
            case 'w':
                self.zoom(x_delta=0, y_delta=-y_span / 10, center=(x_loc, y_loc), axis_selector=ax)
            case 's':
                self.zoom(x_delta=0, y_delta=y_span / 10, center=(x_loc, y_loc), axis_selector=ax)
            case 'a':
                self.zoom(x_delta=-x_span / 10, y_delta=0, center=(x_loc, y_loc), axis_selector=ax)
            case 'd':
                self.zoom(x_delta=x_span / 10, y_delta=0, center=(x_loc, y_loc), axis_selector=ax)
            case 'tab':
                if self.axis_pointer is None:
                    self.axis_pointer = (0, 0)
                elif self.axis_pointer[0] < self.axes.shape[0] - 1:
                    self.axis_pointer = tuple([int(i) for i in array(self.axis_pointer) + [1, 0]])
                elif self.axis_pointer[1] < self.axes.shape[1] - 1:
                    self.axis_pointer = tuple([int(i) for i in array(self.axis_pointer) + [0, 1]])
                else:
                    self.axis_pointer = (0, 0)
                self.highlight_axis()
            case _:
                self.injected_actions['key_pressed'](event)

    def on_key_release(self) -> None:
        """
        Resets the keyboard input
        :return: None
        """
        self.key_pressed = None

    def on_scroll(self, event: MouseEvent | Event) -> None:
        """
        Method to handle scrolling of the mouse
        :param event:  event that has mouse coordinates as well as up or down scrolling motion
        :return: None
        """
        x_span, _, _, _, _ = get_axis_geometry(self.axes[self.axis_pointer])
        if event.button == 'up':
            self.zoom(x_span / 10, 0, center=(event.xdata, event.ydata))
        elif event.button == 'down':
            self.zoom(-x_span / 10, 0, center=(event.xdata, event.ydata))
        else:
            return

    def move_forward(self, amount: float = 0.85):
        """
        Moves plot forward. Forwards the axis of the axis pointer
        :param amount: amount to move the plot forward (factor of x_span)
        :return: None
        """
        x_span, _, _, _, _ = get_axis_geometry(self.axes[self.axis_pointer])
        self.move_by(x_span * amount, 0)

    def move_backward(self, amount: float = 0.85):
        """
        Moves plot backward. Backwards the axis of the axis pointer
        :param amount: amount to move the plot backward (factor of x_span)
        :return: None
        """
        x_span, _, _, _, _ = get_axis_geometry(self.axes[self.axis_pointer])
        self.move_by(-x_span * amount, 0)

    """
    Axis and subplot management
    Methods to create subplots
    """

    def create_figure(self, **kwargs) -> None:
        """
        Creates the figure and the canvas for the graph
        :param kwargs:
        :return:
        """
        self.figure = Figure(**kwargs)
        self.figure.subplots_adjust(top=0.98, bottom=0.08, left=0.08, right=0.98)
        self.canvas = FigureCanvasTkAgg(self.figure, self.root)
        self.canvas.get_tk_widget().pack(fill=BOTH, expand=True, anchor='center')

        # User input handling -
        self.create_subplots((1, 1))  # Creates only one axis epr default. Use 'create subplots' for more

        self.canvas.mpl_connect('axes_enter_event', self.on_axis_enter)
        self.canvas.mpl_connect('axes_leave_event', lambda event: self.on_axis_leave())
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.canvas.mpl_connect('key_release_event', lambda event: self.on_key_release())
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

    def create_subplots(self, shape: tuple[int, int] = (1, 1), sharex=True, **kwargs) -> None:
        """
        Method to create subplots. This will overwrite the old ones and remove their content
        :param shape: Tuple that defines the shape of the subplots in matrix form
        :param sharex: By default, will share the x-axis of all subplots
        :param kwargs: Keyword arguments that go into plt.subplots
        :return:
        """
        self.reset(hard=True)
        if type(shape) is not tuple:
            raise TypeError('Shape has to be a tuple')
        new_axes = self.figure.subplots(*shape, sharex=sharex, **kwargs)
        self.sharex = sharex
        if 'sharey' in kwargs:
            self.sharey = kwargs['sharey']
        if type(new_axes) is not ndarray:
            new_axes = array(new_axes, dtype=object)
        self.axes = new_axes.reshape(shape)
        self.axis_pointer = (0, 0)
        self.highlight_axis()
        self.refresh()

    def add_axis(self, cols: int = 0, rows: int = 1) -> None:
        """
        Adds or subtracts new subplot
        :param cols: Number of columns to be added or subtracted
        :param rows: Number of rows to be added or subtracted
        :return: None
        """
        self.figure.clear()
        # Storing old plot data
        old_axes = []
        for ax in self.axes:
            old_axes.append(ax)
        n_rows, n_cols = self.axes.shape
        self.create_subplots((n_rows + rows, n_cols + cols))

    def use_grid_spec(self,
                      shape: tuple[int, int],
                      specs: list[tuple[int | slice, int | slice]],
                      sharex: bool | list[None | tuple] = True,
                      sharey: bool | list = False, **kwargs) -> None:
        """
        Create axes with GridSpec. This will create axis with uneven sizes. Super complex to use, please check the
        Matlab GridSpec documentation first. self.axes will have None entries after use
        :param sharex: Axes share x-axis if true. If you pass a list, indicate only the master axes for each axis
                        that shares its x. E.g. if you have 3 axes [(0, 0), (3, 0), (4, 0)] as locators in self.axes and
                        you want (4, 0) to share its x with (3, 0) you pass a list like [None, None, (3, 0)] meaning that
                        (4, 0) will get its x from (3, 0).
        :param sharey: Same as sharex
        :param shape: Overall grid shape
        :param specs: List of specs for axes. Defines where axes start and how much they span
        :param kwargs: Keyword arguments that go into GridSpec
        :return: None
        """
        if self.figure is None:
            return
        elif prod(shape) < len(specs):
            raise ValueError(
                'Something is not right with this specification you cannot have more axes than cols x rows')

        self.reset(hard=True)

        if type(sharex) is bool:
            if sharex:
                sharex = [None] + [(0, 0)] * (len(specs) - 1)
            else:
                sharex = [None] * len(specs)
        elif len(sharex) != len(specs):
            raise ValueError('When passing a list for sharex make sure it has the same length as specs')

        if type(sharey) is bool:
            if sharey:
                sharey = [None] + [(0, 0)] * (len(specs) - 1)
            else:
                sharey = [None] * len(specs)
        elif len(sharey) != len(specs):
            raise ValueError('When passing a list for sharex make sure it has the same length as specs')

        self.sharex = sharex
        self.sharey = sharey

        self.axes = full(shape, None)
        grid_spec = GridSpec(*shape, figure=self.figure, **kwargs)

        for i, ax_spec in enumerate(specs):
            start_row = ax_spec[0]
            if type(start_row) is slice:
                start_row = start_row.start
            elif type(start_row) is not int:
                raise TypeError('Elements of specs must be an integer or slice')

            start_col = ax_spec[1]
            if type(start_col) is slice:
                start_col = start_col.start
            elif type(start_col) is not int:
                raise TypeError('Elements of specs must be an integer or slice')

            if sharex[i] is None and sharey[i] is None:
                self.axes[(start_row, start_col)] = self.figure.add_subplot(grid_spec[ax_spec])
            elif sharey[i] is None:
                self.axes[(start_row, start_col)] = self.figure.add_subplot(grid_spec[ax_spec],
                                                                            sharex=self.axes[sharex[i]])
            elif sharex[i] is None:
                self.axes[(start_row, start_col)] = self.figure.add_subplot(grid_spec[ax_spec],
                                                                            sharey=self.axes[sharey[i]])
            else:
                self.axes[(start_row, start_col)] = self.figure.add_subplot(grid_spec[ax_spec],
                                                                            sharey=self.axes[sharey[i]],
                                                                            sharex=self.axes[sharex[i]])

        self.axis_pointer = (0, 0)
        self.highlight_axis()
        self.refresh()

    def show_ecg_grid(self, labels: list[str | float | int] | ndarray[str | float | int],
                      locs: list[int] | ndarray[int], n_bins: int = 4) -> None:
        """
        Method to customize the axis labels of the current axis. This will override the default axis labels to some
        custom value. This method takes its toll on th performance, so I would not recommend to use it. Can be nice
        if you want to see readable time.
        :param labels: List of labels. For each label location there must be a label provided. If the list consists of
                        numeric values, make sure they are in seconds. The function automatically converts numbers.
        :param locs: List of label locations. Corresponds to the x-axis values of the current plot
        :param n_bins: How many values to show on screen
        :return: None
        """

        if len(locs) != len(labels):
            raise ValueError('Number of locs must equal number of labels')

        if all_type_x(labels, [float, int, float16, float32, float64, int8, int16, int32]):
            self.x_customized = True
            self.x_labels_and_ticks = (labels, locs)
            self.x_bins = n_bins
        else:
            raise TypeError('All elements of labels must be numeric')

        for ax in self.axes.flatten():
            if ax is None:
                continue

            x_lim = ax.get_xlim()
            ax.grid(which='major', color='black', linewidth=0.3)
            ax.grid(which='minor', color='red', linewidth=0.1)
            ax.set_xlim(x_lim)
            #ax.tick_params(axis='x', which='major', rotation=30)
            self.update_x_ticks(ax)
            self.refresh(zoom=False)

    # Custom tick update function
    def update_x_ticks(self, axis_selector: tuple | Axes) -> None:
        """
        Method which updates on-screen custom ticks. Since the signal is sampled at some sampling frequency the
        timestamps will not necessarily coincide with the conventional lines on ECG paper (being 0.04s on minor lines
        and 0.2s on major lines). This is why this function is necessary. It makes sure that not more than a specified
        number of major ticks is on screen and scales accordingly with any natural multiple of the base spacing
        (in this case 0.2s major spacing and 0.04s minor spacing). This method is called on every zoom of the screen.
        :param axis_selector: tuple - used to delete a specific axis items only
        :return: None
        """
        if not self.x_customized:
            return
        if type(axis_selector) is Axes:
            ax = axis_selector
        else:
            ax = self.axes[axis_selector]
        x_span, _, _, _, _ = get_axis_geometry(ax)
        num_major_ticks = 20
        # Choose major and minor tick spacing to keep ≤ n ticks on major
        major_spacing = 20  # Using ints to avoid floating point errors
        minor_spacing = 4  # Using ints to avoid floating point errors
        labels, locs = self.x_labels_and_ticks
        scale = (locs[-1] - locs[0]) / (labels[-1] - labels[0])
        while 100 * x_span / (major_spacing * scale) > num_major_ticks:
            major_spacing += major_spacing
            minor_spacing += minor_spacing

        # Snap to nearest multiple of 0.04
        major_spacing = round(major_spacing / 100, 2)
        minor_spacing = round(minor_spacing / 100, 2)
        visible_range = major_spacing * num_major_ticks

        ax.xaxis.set_major_locator(MultipleLocator(major_spacing * scale))
        ax.xaxis.set_minor_locator(MultipleLocator(minor_spacing * scale))

        if visible_range > 3600:
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: convert_to_hour_string(x / scale)))
        elif visible_range > 60:
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: convert_to_minute_string(x / scale)))
        else:
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: convert_to_seconds_string(x / scale)))

    def reset_x_ticks(self) -> None:
        """
        Resets the x_ticks to the default options
        :return: None
        """
        self.x_customized = False
        self.x_labels_and_ticks = None
        self.x_bins = None
        for ax in self.axes.flatten():
            if ax is None:
                continue
            ax.grid(False, which='both')
            ax.tick_params(which='minor', bottom=False, left=False)
            ax.xaxis.set_major_locator(AutoLocator())
            ax.xaxis.set_major_formatter(ScalarFormatter())

    """
    Other functions
    """

    def default_hover_function(self, event: MouseEvent) -> None:
        """
        Default method used to highlight the datapoint which the mouse currently hovers
        :param event: matplotlib.backend_bases.MouseEvent used to get the pointer location
        :return: None
        """
        self.axis_pointer = tuple([int(i[0]) for i in where(event.inaxes == self.axes)])
        if bool(self.axes[self.axis_pointer].lines):
            _, _, _, _, ar = get_axis_geometry(self.axes[self.axis_pointer])
            x_data = self.axes[self.axis_pointer].lines[0].get_xdata()
            y_data = self.axes[self.axis_pointer].lines[0].get_ydata()
            closest_point = find_closest_point((x_data, y_data), (event.xdata, event.ydata),
                                               aspect_ratio=ar / 2,
                                               snap_on_max=self.snap_on_max.get())
            self.hover_coord = (x_data[closest_point], y_data[closest_point])
            self.plot_hover_point(*self.hover_coord)
            self.canvas.draw_idle()

            # Otherwise there could be a weird toggling of the values
            global hide_tick
            hide_tick = False

    def create_master_slider(self) -> None:
        """
        Method to create the master slider tkinter widget used to slide through the signal
        :return: None
        """
        self.master_slider = MasterSlider(self.root, from_=0, to=100, var=self.master_location)
        self.master_slider.config(command=lambda x: self.move_to(x, axis_selector=self.master_axis))

    def initiate_slider(self) -> None:
        """
        Method to initiate and update the slider. Used when figure is zoomed or changed
        :return: None
        """
        if self.data_length is None or self.master_slider is None:
            return
        x_span, _, _, _, _ = get_axis_geometry(self.axes[self.master_axis])
        self.master_slider.update_slider(data_length=self.data_length, window_size=x_span,
                                         location=self.master_location.get())


# Test run -------------------------------------------------
if __name__ == '__main__':
    # Test code to see if the screen works
    #
    #
    # Getting the data to display
    data = DataHandler()
    data.get_file()
    data.open_file()
    # Starting tkinter
    root = Tk()
    app = GraphHandler(container=root)
    # Defining the axes
    app_shape = (3, 3)
    app_specs = [(slice(0, 2), slice(0, 3)), (2, 0), (2, 1), (2, 2)]
    app.use_grid_spec(app_shape, app_specs)
    for spec in [(2, 0), (2, 1), (2, 2)]:
        app.axes[spec].xaxis.set_visible(False)
    # Plotting data
    app.plot_line_plot(data['Index'], data['ecg [uV]'], name='ecg [uV]', label='ecg [uV]', color='k', slider=True)
    app.plot_scatter_plot(data['Index'], data['Label: R_peak'] * data['ecg [uV]'], name='R peaks')
    app.show_x_window(0, 1500)

    root.mainloop()
