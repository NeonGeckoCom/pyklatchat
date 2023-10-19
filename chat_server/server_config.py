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
from typing import Optional

from config import Configuration
from chat_server.server_utils.sftp_utils import init_sftp_connector
from utils.logging_utils import LOG
from utils.database_utils import DatabaseController

server_config_path = os.environ.get(
    "CHATSERVER_CONFIG", "~/.local/share/neon/credentials.json"
)
database_config_path = os.environ.get(
    "DATABASE_CONFIG", "~/.local/share/neon/credentials.json"
)


def _init_db_controller(db_config: dict) -> Optional[DatabaseController]:
    from chat_server.server_utils.db_utils import DbUtils

    # Determine configured database dialect
    dialect = db_config.pop("dialect", "mongo")

    try:
        # Create a database connection
        db_controller = DatabaseController(config_data=db_config)
        db_controller.attach_connector(dialect=dialect)
        db_controller.connect()
    except Exception as e:
        LOG.exception(f"DatabaseController init failed: {e}")
        return None

    # Initialize convenience class
    DbUtils.init(db_controller)
    return db_controller


if os.path.isfile(server_config_path) or os.path.isfile(database_config_path):
    LOG.warning(f"Using legacy configuration at {server_config_path}")
    LOG.warning(f"Using legacy configuration at {database_config_path}")
    LOG.info(f"KLAT_ENV : {Configuration.KLAT_ENV}")
    config = Configuration(from_files=[server_config_path, database_config_path])
    app_config = config.get("CHAT_SERVER", {}).get(Configuration.KLAT_ENV, {})
    db_controller = config.get_db_controller(name="pyklatchat_3333")
else:
    # ovos-config has built-in mechanisms for loading configuration files based
    # on envvars, so the configuration structure is simplified
    from ovos_config.config import Configuration
    app_config = Configuration().get("CHAT_SERVER") or dict()
    env_spec = os.environ.get("KLAT_ENV")
    if env_spec and app_config.get(env_spec):
        LOG.warning("Legacy configuration handling KLAT_ENV envvar")
        app_config = app_config.get(env_spec)
    db_controller = _init_db_controller(app_config.get("connection_properties",
                                                       Configuration().get(
                                                           "DATABASE_CONFIG",
                                                           {})))

LOG.info(f"App config: {app_config}")

sftp_connector = init_sftp_connector(config=app_config.get("SFTP", {}))
