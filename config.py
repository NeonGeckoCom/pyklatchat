# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Elon Gasper, Richard Leeds, Kirill Hrymailo
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending

import os
import json
import copy

from typing import List
from neon_utils import LOG

from utils.database_utils import DatabaseController


class Configuration:

    db_controllers = dict()

    def __init__(self, from_files: List[str]):
        self._config_data = dict()
        for source_file in from_files:
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

    def get_db_controller(self, name: str, override: bool = False, override_args: dict = None) -> DatabaseController:
        """
            Returns an new instance of Database Controller for specified dialect (creates new one if not present)

            :param name: db connection name from config
            :param override: to override existing instance under :param dialect (defaults to False)
            :param override_args: dict with arguments to override (optional)

            :returns instance of Database Controller
        """
        db_controller = self.db_controllers.get(name, None)
        if not db_controller or override:
            db_config = copy.deepcopy(self.config_data.get('DATABASE_CONFIG', {}).get(os.environ.get('ENV'), {})
                                      .get(name, {}))
            # Overriding with "override args" if needed
            if not override_args:
                override_args = {}
            db_config = {**db_config, **override_args}

            dialect = db_config.pop('dialect', None)
            if dialect:
                db_controller = DatabaseController(config_data=db_config)
                db_controller.attach_connector(dialect=dialect)
                db_controller.connect()
        return db_controller
