"""
Data handler class. Takes care of CSV data for the app.

Author: Victor Gutgesell
Version: 1.1
"""

# Import packages ----------------------------------------------
import os
import numpy as np
import pandas as pd
from tkinter import filedialog, messagebox
import pandas.api.types as pat

# Import functions from other scripts ----------------------
from utils.helpers import get_default_annotations

# Global variable ----------------------------------------------
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_HEARTBEAT_CLASSES = get_default_annotations()['heartbeat_classes']
SEGMENT_DENOMINATORS = get_default_annotations()['segment_denominators']


# Classes ------------------------------------------------------
class DataHandler:
    """
    Creates an instance of the DataHandler class which at its core contains a Pandas Dataframe.
    This class can open a text or csv file with an openfile dialogue and save it after.
    """

    def __init__(self):
        self.time_axes = []
        self.plottable_axes = []
        self.label_list = []
        self.data_directory = None
        self.extension = None
        self.data_path = None
        self.plot_data = None
        self.filename = None
        self.selected_label = ''
        self.in_app = False
        self.y_axis_header = None
        self.x_axis_header = None
        self.delimiter = ','

    def __len__(self) -> int:
        return len(self.plot_data)

    def __getitem__(self, item: int | slice | str | tuple[int, str] | list[int | str]) \
            -> pd.DataFrame | None | float:
        """
        Get-item method to index the DataHandler object with []
        :param item: item to retrieve. Can be int, slice, string, tuple, list.
        :return: Pandas dataframe, Series of numpy ndarray, depending on item input.
        """
        if self.plot_data is None:
            return
        if type(item) in [int, slice]:
            return self.plot_data.loc[item]
        elif type(item) in [list, tuple]:
            if all(isinstance(i, str) for i in item):
                return self.plot_data[item]
            else:
                return self.plot_data.loc[item]
        elif type(item) is str:
            if item.lower() == 'index':
                return pd.Series(self.plot_data.index, name='index')
            return self.plot_data[item]

    def reset(self):
        """
        Method to reset the data_handler instance
        :return:
        """
        delimiter = self.delimiter
        in_app = self.in_app
        self.__init__()
        self.delimiter = delimiter
        self.in_app = in_app

    def info(self):
        """
        Print information about the data_handler instance
        :return:
        """
        print(f'Filename: {self.filename}')
        print(f'Data directory: {self.data_directory}')
        print('--------------------------------------------')
        print(f'Columns: {self.plot_data.columns}')
        print(f'Dtypes: {self.plot_data.dtypes.values}')
        print('---------------------------------------------')
        print(f'Length: {len(self)}')

    def reset_data_variables(self) -> None:
        """
        Reset global settings for in-app options
        :return:
        """
        self.time_axes = []
        self.plottable_axes = []
        self.label_list = []
        self.plot_data = None
        self.selected_label = ''
        self.y_axis_header = None
        self.x_axis_header = None

    def set_delimiter(self, delimiter: str):
        """
        Method to set a file delimiter. Used when opening a new project file (see self.open_file)
        :param delimiter: string. Delimiter for the files to open. Is , per default
        :return: None
        """
        self.delimiter = delimiter

    """
    Some methods from pandas dataframe
    """

    def drop(self, *args, **kwargs):
        self.plot_data.drop(*args, **kwargs)

    def fill_nans(self, *args, **kwargs):
        self.plot_data.fillna(*args, **kwargs)

    def get_columns(self):
        return self.plot_data.columns

    """
    Methods to obtain class-specific data
    """

    def set_selected_label(self, label_name: str) -> None:
        """
        Method to set the selected label. If it does not yet exist, it will be created.
        :param label_name: String - Name of label
        :return: None
        """
        if self.plot_data is None:
            return

        if type(label_name) is not str:
            raise TypeError('label_name must be a string')

        if label_name not in self.label_list:
            self.declare_label(label_name)
        self.selected_label = label_name

    def get_xy_pair(self, x_column: str, y_column: str, dropna: bool = True) -> np.ndarray:
        """
        Method to obtain an array of shape (2, N) which can be used to plot x-y pairs of data from the DataHandler
        :param dropna:
        :param x_column: string - label of the x-axis column
        :param y_column: string - label of the y-axis column
        :return: numpy array of shape (2, N)
        """
        if self.plot_data is None:
            return np.array([])
        if x_column.lower() == 'index' and y_column.lower() == 'index':
            raise ValueError(f'{x_column} and {y_column} are not compatible')
        elif x_column.lower() == 'index':
            df = self[y_column].copy()
        elif y_column.lower() == 'index':
            df = self[x_column].copy()
        else:
            df = self[[x_column, y_column]].copy()
        if dropna:
            df.dropna(inplace=True, axis=0)
        if x_column.lower() == 'index':
            return np.array([df.index.values, df.values])
        elif y_column.lower() == 'index':
            return np.array([df.values, df.index.values])
        else:
            return np.array([df[x_column].values, df[y_column].values])

    def get_label_data(self, label: str | list | None, inverse=False) -> pd.DataFrame:
        """
        Method to return df of a certain label
        :param label: string of label name in question
        :param inverse: If true, returns where label was not selected
        :return:
        """
        if label is None:
            label = self.selected_label
        if type(label) is not list:
            label = [label]
        for num, l in enumerate(label):
            if 'Label: ' not in l:
                label[num] = f'Label: {l}'
            if label[num] not in self.get_columns():
                raise ValueError(f'Label {label[num]} not found in DataHandler')
        if inverse:
            label_data = self.plot_data.loc[self[label].eq(None).any(axis=1)].copy()
        else:
            label_data = self.plot_data.loc[self[label].eq(1).any(axis=1)].copy()

        # Adding index column
        label_data['Index'] = label_data.index

        return label_data

    def get_label_list(self) -> None:
        """
        Method to extract all previously assigned labels from the dataset
        :return:
        """
        self.label_list = []
        for label in self.plot_data.columns:
            if 'Label: ' in label:
                self.label_list.append(label.removeprefix('Label: '))
        if not len(self.label_list) == 0 and self.in_app:
            self.selected_label = self.label_list[0]

    def get_time_axes_in_seconds(self) -> list | None:
        """
        Method that retrieves all axes from data which can be used as y-axis
        :return: None
        """
        if self.plot_data is None:
            return
        self.time_axes = []
        # Iterate through dataframe headers
        # If a header contains keyword 'time' it is selected as a time axis
        # Only takes numeric data
        # Converts to seconds automatically
        for column in self.get_columns():
            if 'time' in str(column).lower() and pat.is_numeric_dtype(self[column]):

                if '[ns]' in str(column).lower():
                    unit = 'ns'
                    new_column = column.replace('[ns]', '[s]')
                    if 'timestamp' in str(column).lower():
                        new_column = new_column.replace('timestamp', 'timer')

                elif '[ms]' in str(column).lower():
                    unit = 'ms'
                    new_column = column.replace('[ms]', '[s]')
                    if 'timestamp' in str(column).lower():
                        new_column = new_column.replace('timestamp', 'timer')

                elif '[s]':
                    unit = 's'
                    new_column = column
                    if 'timestamp' in str(column).lower():
                        new_column = new_column.replace('timestamp', 'timer')

                self.seconds_from_time_series(column, new_column, unit=unit)

                if new_column not in self.time_axes:
                    self.time_axes.append(new_column)

            # Ignore all columns that do not feature the word 'time'
            else:
                continue

            if not bool(self.time_axes):
                self.x_axis_header = 'Index'
            else:
                self.x_axis_header = self.time_axes[0]

        return self.time_axes

    def get_plottable_axes(self) -> list | None:
        """
        Method that retrieves all axes from data which can be used as y-axis
        :return:
        """
        if self.plot_data is None:
            return
        self.plottable_axes = []
        # Iterate through dataframe headers
        for column in self.get_columns().values:
            if 'Label: ' in column:
                continue
            elif 'Original: ' in column:
                continue
            elif 'Index' in column:
                continue
            elif 'time' in column.lower():
                continue
            elif not pat.is_numeric_dtype(self[column]):
                continue
            else:
                self.plottable_axes.append(column)
        if ((self.y_axis_header is None)
                and (self.y_axis_header not in self.plottable_axes)
                and bool(self.plottable_axes)):
            self.y_axis_header = self.plottable_axes[0]

        return self.plottable_axes

    def get_last_label_location(self, label: str | list | None = None) -> float | None:
        """
        Returns the last index of a label column
        :param label:
        :return:
        """
        if label is None:
            label = f'Label: {self.selected_label}'
        if type(label) is not list:
            label = [label]
        condition = self.plot_data.loc[self[label].eq(1).any(axis=1)]
        if condition.empty:
            return None
        elif self.x_axis_header.lower() == 'index':
            return max(condition.index.values)
        else:
            return max(condition[self.x_axis_header].values)

    def get_heartbeats(self) -> list[pd.DataFrame | None]:
        """
        Method to obtain all heartbeats from ECG Data. This will return all datapoints where either of the
        default heartbeat classes is present
        :return: DataFrame with heartbeats or None
        """
        if (self.plot_data is None) or not bool(self.label_list):
            return []
        present_labels = []
        for key in DEFAULT_HEARTBEAT_CLASSES.keys():
            if key in self.label_list:
                present_labels.append(key)
        heartbeats = self.get_label_data(present_labels)
        heartbeats['Index'] = heartbeats.index

        # Check which of the segment breakers are in the datas et
        included_markers = []
        for marker in list(SEGMENT_DENOMINATORS.keys()):
            if marker in self.label_list:
                included_markers.append(marker)

        # If there are no segment breaks return list with one pd.Dataframe
        if len(included_markers) == 0:
            return [heartbeats]

        # Breaking it into segments (if there are breaks in the record)
        breaks = self.get_label_data(included_markers)['Index'].values
        heartbeat_segments = []

        # This loop splits the heartbeats apart where a ~ denominates a noisy segment
        step = 0
        last_break = 0
        segmenting = True
        while segmenting:
            if step >= len(breaks):
                segment = heartbeats.loc[last_break:].copy()
            else:
                segment = heartbeats.loc[last_break:breaks[step]].copy()
            if segment.empty:
                step += 1
                continue
            heartbeat_segments.append(segment)
            last_break = segment.index.values[-1] + 1
            remainder = heartbeats.loc[heartbeats['Index'] > last_break]
            if remainder.empty:
                segmenting = False
            else:
                last_break = remainder.index.values[0]
            step += 1

        return heartbeat_segments

    """
    File management functionality
    """

    def open_file_no_gui(self, filepath: str) -> None:
        """
        Method to open a file - for use in iPython Notebook
        :param filepath: String for filename. Use absolute paths
        :return:
        """
        self.reset()
        self.data_path = filepath.replace(r'\\'[0], r'/')
        # In case this code is used stand-alone, the selected label variable will not be used
        if self.in_app:
            self.selected_label = 'Default'
        # Get type and name of file
        self.filename = ''.join(self.data_path.split('/')[-1].split('.')[0:-1])
        self.extension = self.data_path.split('.')[-1]
        self.data_directory = os.path.dirname(self.data_path)
        self.open_file()

    def get_file(self) -> None:
        """
        Method that opens a file dialogue pop-up to open a text or csv file, which can either be a new csv style type
        file or an existing project.
        :return: None
        """
        if self.data_directory is None:
            default_dir = 'C:/'
        else:
            default_dir = self.data_directory

        # Get .csv or .txt file to open in a file dialogue window
        path = filedialog.askopenfilename(title="Select a file",
                                          filetypes=[("CSV files", "*.csv*"),
                                                     ("Text files", "*.txt")],
                                          initialdir=default_dir)
        if path == '':  # Handles the case that the user closes the window
            # Throw an error box
            raise ValueError('No file was selected')
        self.reset()
        self.data_path = path.replace(r'\\'[0], r'/')
        if self.in_app:  # In case this code is used stand-alone, the selected label variable will not be used
            self.selected_label = 'Default'
        self.filename = ''.join(self.data_path.split('/')[-1].split('.')[0:-1])
        self.extension = self.data_path.split('.')[-1]
        self.data_directory = os.path.dirname(self.data_path)

    def open_file(self) -> None:
        """
        Method to open a filepath and load in pandas dataframe
        :return: None
        """
        # Handling of file processing depending on opening
        if self.extension.lower() in ['csv', 'txt']:
            self.reset_data_variables()
            if self.extension == 'txt':
                self.set_delimiter(';')
            elif self.extension == 'csv':
                self.set_delimiter(',')
            self.plot_data = pd.read_csv(self.data_path, delimiter=self.delimiter)
            self.get_label_list()
            self.get_plottable_axes()
            self.get_time_axes_in_seconds()
        else:
            raise TypeError('Extension must be ".txt" or ".csv"')

    def get_and_open_file(self):
        self.get_file()
        self.open_file()

    def save_file_as(self) -> None:
        """
        Method to save current project file as pandas dataframe
        :return:
        """
        if self.plot_data is None:  # Checks if data is loaded
            # Throw an error
            raise ValueError('No data to store')

        # Get the desired filename form the user
        save_filename = filedialog.asksaveasfilename(title='Save File',
                                                     filetypes=[("CSV files", "*.csv*")],
                                                     initialfile=self.filename,
                                                     defaultextension='.csv')
        if save_filename == '':
            # Throw an error
            raise ValueError('No file was declared for saving')
        self.data_directory = os.path.dirname(save_filename)
        self.filename = save_filename.split('/')[-1].split('.')[0]
        # Save the file as csv
        self.plot_data.to_csv(save_filename, index=False)

    def save_file(self) -> None:
        """
        Method to save current project file as pandas dataframe in last location as csv
        :return:
        """
        if self.plot_data is None:  # Checks if data is loaded
            # Throw an error
            raise ValueError('No data to store')
        save_filename = f'{self.data_directory}/{self.filename}.csv'
        # Save the file as csv
        self.plot_data.to_csv(save_filename, index=False)
        message_str = f'File saved successfully under: \n{save_filename}'
        if self.in_app:
            messagebox.showinfo(title='Saved Successfully', message=message_str)
        else:
            print(message_str)

    """ 
    # Methods to augment dataframe
    """

    def declare_label(self, label_name: str) -> None:
        """
        Method to declare a new label in the dataset
        :param label_name:
        :return:
        """
        if not bool(label_name):
            return
        if f'Label: {label_name}' in self.get_columns():
            raise ValueError(f'The label {label_name} already exists')
        self.selected_label = label_name
        self.plot_data[f'Label: {label_name}'] = None
        self.label_list.append(label_name)

    # Methods to manipulate the data
    def toggle_selected_label(self, index: int, label: str | None = None) -> bool:
        """
        Method that toggles a label value between 1 and None for a selected label
        :param label: String - which label to toggle
        :param index: integer in the signal
        :return Adding: Boolean to indicate if a label was added or removed
        """
        if label is None:
            label = self.selected_label
        # Check if the selected label exists and is a part of the dataset
        if not (f'Label: {label}' in self.get_columns()):
            raise KeyError(f'Declare a label before selecting')
        # Toggle value between 1 and None
        if self.plot_data.loc[index, f'Label: {label}'] == 1:
            self.plot_data.loc[index, f'Label: {label}'] = None
            return True
        else:
            self.plot_data.loc[index, f'Label: {label}'] = 1
            return False

    def seconds_from_time_series(self, axis: str, new_axis: str | None = None, unit='ns') -> None:
        """
        Method to convert an axis of time to relative time axis
        :param new_axis: New axis name. If None, will transform inplace
        :param axis: Axis that contains time information (must be axis to contain float or int)
        :param unit: Unit of measure of original axis
        :return: None
        """
        if not pat.is_numeric_dtype(self[axis]):
            raise TypeError(f'Axis {axis} must be numeric')
        # Match case of unit conversion
        if unit in ['ns', 'nanoseconds', 'nano']:
            power = 1e9
        elif unit in ['us', 'microseconds', 'micro']:
            power = 1e6
        elif unit in ['ms', 'milliseconds', 'milli']:
            power = 1e3
        else:
            power = 1
        # Convert axis
        values = (self[axis] - self[axis][0]) / power
        if new_axis is None:
            new_axis = axis
        self.plot_data[new_axis] = values


# Testing--------------------------------------------------
if __name__ == '__main__':
    data = DataHandler()
    data.get_file()
    data.open_file()
