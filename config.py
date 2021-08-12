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

from utils.database.db_controller import DatabaseController, DatabaseConnector


class Configuration:

    db_controllers = dict()

    def __init__(self, file_path: str):
        with open(os.path.expanduser(file_path)) as input_file:
            self._config_data = json.load(input_file)

    @property
    def config_data(self) -> dict:
        return self._config_data

    @config_data.setter
    def config_data(self, value):
        if not isinstance(value, dict):
            raise TypeError(f'Type: {type(value)} not supported')
        self._config_data = value

    def get_db_controller(self,
                          dialect: str,
                          override: bool = False) -> DatabaseController:
        """
            Returns an new instance of Database Controller for specified dialect (creates new one if not present)

            :param dialect: Database dialect
            :param override: to override existing instance under :param dialect

            :returns instance of Database Controller
        """
        config_data = self.config_data.get('CHAT_SERVER', {}).get(os.environ.get('ENV'), {})
        db_controller = self.db_controllers.get(dialect, None)
        if not db_controller or override:
            db_controller = DatabaseController(config_data=config_data)
            db_controller.attach_connector(dialect=dialect)
            db_controller.connect()
        return db_controller
