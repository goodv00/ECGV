"""
Functions used throughout the app

Author: Victor Gutgesell
Version: 1.0
"""

# Import packages-------------------------------------------
import os
import json
from numpy import ndarray, argmax, argmin, sqrt, array, where

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

def find_closest_point(data: ndarray[[float], [float]] | list[[float], [float]],
                       target: tuple[float, float],
                       aspect_ratio: float = 1,
                       snap_on_max: int = 0) -> int:
    """
    Function to find the closest point in an x-y dataset
    :param data: x-y dataset - numpy array of shape (2, N)
    :param target: tuple - target datapoint
    :param aspect_ratio: float - aspect ratio to correct skewed on-screen display of data
    :param snap_on_max: int - if 1 the found point will snap on the highest y-datapoint in the vicinity of index
    :return: int
    """
    x_data, y_data = data
    index = argmin(sqrt(((array(x_data).astype(float) - target[0]) / aspect_ratio) ** 2 +
                        (array(y_data).astype(float) - target[1]) ** 2))
    # Snap-on functionality
    if snap_on_max == 1:
        if index <= 5:
            index = where(x_data == x_data[0:12][argmax(y_data[0: 12])])[0][0]
        elif index >= len(y_data) - 1:
            index = where(x_data == x_data[-12: -1][argmax(y_data[-12: -1])])[0][0]
        else:
            index = where(x_data == x_data[index - 6: index + 6][argmax(y_data[index - 6: index + 6])])[0][0]
    return index

def all_type_x(data: list[any] | ndarray[any], x_type: type | list[type]) -> bool:
    """
    Checks if all elements inside an array-like object are of a specific type. Returns a bool
    :param data: array-like object with data
    :param x_type: type of list of types to check
    :return: Bool
    """
    if type(x_type) is list:
        return all([[type(i) is x for i in data] for x in x_type])
    elif type(x_type) is type:
        return all([type(i) is x_type for i in data])
    else:
        raise TypeError('x_type must be a type')

def get_default_annotations(file_path: str | None = None) -> dict:
    """
    Gets default annotations from json file and returns them as a dictionary
    :return:
    """
    if file_path is None:
        current_path = os.getcwd()
        if current_path.split('\\')[-1] in ['utils', 'modules', 'screens', 'analysis', 'misc']:
            parent_path = os.path.dirname(current_path)
        else:
            parent_path = current_path
        file_path = parent_path + '\\analysis\\default_annotations.json'
    with open(file_path, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    annotations = get_default_annotations()


