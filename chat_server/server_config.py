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

from neon_sftp import NeonSFTPConnector
from kubernetes import client, config
from klatchat_utils.configuration import KlatConfigurationBase
from klatchat_utils.exceptions import MalformedConfigurationException
from klatchat_utils.database_utils import DatabaseController
from klatchat_utils.database_utils.mongo_utils.queries.wrapper import MongoDocumentsAPI

from chat_server.server_utils.sftp_utils import init_sftp_connector
from chat_server.server_utils.rmq_utils import RabbitMQAPI


class KlatServerConfig(KlatConfigurationBase):

    db_controllers = dict()

    def __init__(self):
        super().__init__()

        self._sftp_connector = None
        self._default_db_controller = None
        self._k8s_config = None
        self._k8s_default_namespace = None
        self._k8s_api = None
        self._mq_api = None
        self._mq_management_config = None

        MongoDocumentsAPI.init(
            db_controller=self.default_db_controller, sftp_connector=self.sftp_connector
        )

    @property
    def config_key(self) -> str:
        return "CHAT_SERVER"

    @property
    def required_sub_keys(self) -> tuple[str]:
        return (
            "COOKIES",
            "FILE_STORING_TYPE",
            "LIBRE_TRANSLATE_URL",
            "MQ_MANAGEMENT",
            "DATABASE_CONFIG",
        )

    @property
    def sftp_connector(self) -> NeonSFTPConnector:
        if not self._sftp_connector:
            self._sftp_connector = init_sftp_connector(
                config=self.config_data.get("SFTP")
            )
        return self._sftp_connector

    @property
    def k8s_config(self) -> dict:
        return self.config_data.get("K8S_CONFIG", {})

    @property
    def k8s_default_namespace(self) -> str:
        if not self._k8s_default_namespace:
            self._k8s_default_namespace = self.k8s_config.get(
                "K8S_DEFAULT_NAMESPACE", "default"
            )
        return self._k8s_default_namespace

    @property
    def k8s_api(self):
        if not self._k8s_api:
            if _k8s_config_path := self.k8s_config.get("K8S_CONFIG_PATH"):
                config.load_kube_config(_k8s_config_path)
                self._k8s_api = client.AppsV1Api()
            raise MalformedConfigurationException(
                message="'K8S_CONFIG_PATH' property is missing in 'K8S_CONFIG'"
            )
        return self._k8s_api

    @property
    def mq_management_config(self) -> dict:
        return self.config_data.get("MQ_MANAGEMENT", {})

    @property
    def mq_api(self) -> RabbitMQAPI:
        if not self._mq_api:
            if mq_management_url := self.mq_management_config.get("MQ_MANAGEMENT_URL"):
                self._mq_api = RabbitMQAPI(url=mq_management_url)
                self._mq_api.login(
                    username=self.mq_management_config["MQ_MANAGEMENT_LOGIN"],
                    password=self.mq_management_config["MQ_MANAGEMENT_PASSWORD"],
                )
            else:
                raise MalformedConfigurationException(
                    message="'MQ_MANAGEMENT_URL' property is missing in 'MQ_MANAGEMENT'"
                )
        return self._mq_api

    @property
    def default_db_controller(self):
        if not self._default_db_controller:
            self._default_db_controller = self.get_db_controller()
        return self._default_db_controller

    def get_db_controller(
        self, name: str = None, override: bool = False, override_args: dict = None
    ):
        """
        Returns an new instance of Database Controller for specified dialect (creates new one if not present)

        :param name: db connection name from config
        :param override: to override existing instance under :param dialect (defaults to False)
        :param override_args: dict with arguments to override (optional)

        :returns instance of Database Controller
        """
        db_controller = self.db_controllers.get(name, None)
        if not db_controller or override:
            db_config = self._get_db_config_from_key(key=name)
            # Overriding with "override args" if needed
            if not override_args:
                override_args = {}
            db_config = {**db_config, **override_args}

            dialect = db_config.pop("dialect", None)
            if dialect:
                db_controller = DatabaseController(config_data=db_config)
                db_controller.attach_connector(dialect=dialect)
                db_controller.connect()
        return db_controller

    def _get_db_config_from_key(self, key: str = None):
        """Gets DB configuration by key"""
        if key is None:
            key = self.config_data.get("DATABASE_CONFIG", {})["__default_alias"]
        return self.config_data.get("DATABASE_CONFIG", {}).get(key, {})


server_config = KlatServerConfig()
