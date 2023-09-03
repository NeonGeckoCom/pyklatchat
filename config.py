# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import json

from os.path import isfile, join, dirname
from typing import List
from ovos_config.config import Configuration as OVOSConfiguration


from utils.logging_utils import LOG


def load_config() -> dict:
    """
        Load and return a configuration object,
    """
    legacy_config_path = "/app/app/config.json"
    if isfile(legacy_config_path):
        LOG.warning(f"Deprecated configuration found at {legacy_config_path}")
        with open(legacy_config_path) as f:
            config = json.load(f)
        LOG.debug(f'Loaded config - {config}')
        return config
    config = OVOSConfiguration()
    if not config:
        LOG.warning(f"No configuration found! falling back to defaults")
        default_config_path = join(dirname(__file__), "default_config.json")
        with open(default_config_path) as f:
            config = json.load(f)
    return config


class Configuration:
    """ Generic configuration module"""

    KLAT_ENV = os.environ.get('KLAT_ENV', 'DEV')
    db_controllers = dict()

    def __init__(self, from_files: List[str]):
        self._config_data = dict()
        for source_file in [file for file in list(set(from_files)) if file]:
            self.add_new_config_properties(self.extract_config_from_path(source_file))

    @staticmethod
    def extract_config_from_path(file_path: str) -> dict:
        """
            Extracts configuration dictionary from desired file path

            :param file_path: desired file path

            :returns dictionary containing configs from target file, empty dict otherwise
        """
        try:
            with open(os.path.expanduser(file_path)) as input_file:
                extraction_result = json.load(input_file)
        except Exception as ex:
            LOG.error(f'Exception occurred while extracting data from {file_path}: {ex}')
            extraction_result = dict()
        # LOG.info(f'Extracted config: {extraction_result}')
        return extraction_result

    def add_new_config_properties(self, new_config_dict: dict, at_key: str = None):
        """
            Adds new configuration properties to existing configuration dict

            :param new_config_dict: dictionary containing new configuration
            :param at_key: the key at which to append new dictionary
                            (optional but setting that will reduce possible future key conflicts)
        """
        if at_key:
            self.config_data[at_key] = new_config_dict
        else:
            # merge existing config with new dictionary (python 3.5+ syntax)
            self.config_data = {**self.config_data, **new_config_dict}

    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def __getitem__(self, key):
        return self.config_data.get(key)

    def __setitem__(self, key, value):
        self.config_data[key] = value

    @property
    def config_data(self) -> dict:
        if not self._config_data:
            self._config_data = dict()
        return self._config_data

    @config_data.setter
    def config_data(self, value):
        if not isinstance(value, dict):
            raise TypeError(f'Type: {type(value)} not supported')
        self._config_data = value

    def get_db_config_from_key(self, key: str):
        """Gets DB configuration by key"""
        return self.config_data.get('DATABASE_CONFIG', {}).get(self.KLAT_ENV, {}).get(key, {})

    def get_db_controller(self, name: str,
                          override: bool = False,
                          override_args: dict = None):
        """
            Returns an new instance of Database Controller for specified dialect (creates new one if not present)

            :param name: db connection name from config
            :param override: to override existing instance under :param dialect (defaults to False)
            :param override_args: dict with arguments to override (optional)

            :returns instance of Database Controller
        """
        from chat_server.server_utils.db_utils import DbUtils

        db_controller = self.db_controllers.get(name, None)
        if not db_controller or override:
            db_config = self.get_db_config_from_key(key=name)
            # Overriding with "override args" if needed
            if not override_args:
                override_args = {}
            db_config = {**db_config, **override_args}

            dialect = db_config.pop('dialect', None)
            if dialect:
                from utils.database_utils import DatabaseController

                db_controller = DatabaseController(config_data=db_config)
                db_controller.attach_connector(dialect=dialect)
                db_controller.connect()
                DbUtils.init(db_controller)
        return db_controller
