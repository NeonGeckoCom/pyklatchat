import os
import json


class Configuration:

    @property
    def config_data(self) -> dict:
        return self._config_data

    @config_data.setter
    def config_data(self, value):
        if not isinstance(value, dict):
            raise TypeError(f'Type: {type(value)} not supported')
        self._config_data = value

    def __init__(self, file_path: str):
        with open(os.path.expanduser(file_path)) as input_file:
            self._config_data = json.load(input_file)
