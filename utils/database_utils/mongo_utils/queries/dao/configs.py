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

from chat_server.server_utils.http_exceptions import ItemNotFoundException
from utils.database_utils.mongo_utils import MongoDocuments, MongoFilter
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.logging_utils import LOG


class ConfigsDAO(MongoDocumentDAO):
    @property
    def document(self):
        return MongoDocuments.CONFIGS

    def get_by_name(self, config_name: str, version: str = "latest"):
        filters = [
            MongoFilter(key="name", value=config_name),
            MongoFilter(key="version", value=version),
        ]
        item = self.get_item(filters=filters)
        if item:
            return item.get("value")
        else:
            LOG.error(f"Failed to get config by {config_name = }, {version = }")
            raise ItemNotFoundException

    def update_by_name(self, config_name: str, data: dict, version: str = "latest"):
        filters = [
            MongoFilter(key="name", value=config_name),
            MongoFilter(key="version", value=version),
        ]
        return self.update_item(filters=filters, data={"value": data})
