# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 Neongecko.com Inc.
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
from abc import ABC, abstractmethod

from os.path import isfile, join, dirname

from klatchat_utils.logging_utils_aggregators import init_log_aggregators
from ovos_config.config import Configuration as OVOSConfiguration

from klatchat_utils.exceptions import MalformedConfigurationException
from klatchat_utils.logging_utils import LOG


class KlatConfigurationBase(ABC):
    """Generic configuration module"""

    def __init__(self):
        self._config_data: dict = None
        self._init_ovos_config()
        if not self._config_data:
            LOG.warning(
                f"OVOS Config does not contain required key = {self.config_key}, "
                f"trying setting up legacy config"
            )
            self._init_legacy_config()
        self._config_data = self._config_data[self.config_key]
        self.validate_provided_configuration()
        init_log_aggregators(config=self.config_data)

    def _init_ovos_config(self):
        ovos_config = _load_ovos_config()
        if self.config_key in ovos_config:
            self._config_data = ovos_config

    def _init_legacy_config(self):
        legacy_config_path = os.path.expanduser(
            os.environ.get(
                f"{self.config_key}_CONFIG", "~/.local/share/neon/credentials.json"
            )
        )
        self.add_new_config_properties(
            self.extract_config_from_path(legacy_config_path)
        )

    def validate_provided_configuration(self):
        for key in self.required_sub_keys:
            if key not in self._config_data:
                return MalformedConfigurationException(
                    f"Required configuration {key = !r} is missing"
                )

    @property
    @abstractmethod
    def required_sub_keys(self) -> tuple[str]:
        pass

    @property
    @abstractmethod
    def config_key(self) -> str:
        pass

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
            self.config_data |= new_config_dict

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
            raise TypeError(f"Type: {type(value)} not supported")
        self._config_data = value

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
            LOG.error(
                f"Exception occurred while extracting data from {file_path}: {ex}"
            )
            extraction_result = dict()
        # LOG.info(f'Extracted config: {extraction_result}')
        return extraction_result


def _load_ovos_config() -> dict:
    """
    Load and return a configuration object,
    """
    legacy_config_path = "/app/app/config.json"
    if isfile(legacy_config_path):
        LOG.warning(f"Deprecated configuration found at {legacy_config_path}")
        with open(legacy_config_path) as f:
            config = json.load(f)
        LOG.debug(f"Loaded config - {config}")
        return config
    config = OVOSConfiguration()
    if not config:
        LOG.warning(f"No configuration found! falling back to defaults")
        default_config_path = join(dirname(__file__), "default_config.json")
        with open(default_config_path) as f:
            config = json.load(f)
    return dict(config)
