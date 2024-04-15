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

# DAO Imports
from utils.database_utils.mongo_utils.queries.dao.abc import MongoDocumentDAO
from utils.database_utils.mongo_utils.queries.dao.configs import ConfigsDAO
from utils.database_utils.mongo_utils.queries.dao.users import UsersDAO
from utils.database_utils.mongo_utils.queries.dao.chats import ChatsDAO
from utils.database_utils.mongo_utils.queries.dao.shouts import ShoutsDAO
from utils.database_utils.mongo_utils.queries.dao.prompts import PromptsDAO
from utils.database_utils.mongo_utils.queries.dao.personas import PersonasDAO


class MongoDAOGateway(type):
    def __getattribute__(self, name):
        item = super().__getattribute__(name)
        try:
            if issubclass(item, MongoDocumentDAO):
                item = item(
                    db_controller=self.db_controller, sftp_connector=self.sftp_connector
                )
        except:
            pass
        return item


class MongoDocumentsAPI(metaclass=MongoDAOGateway):
    """
    Wrapper for DB commands execution
    If getting attribute is triggered, initialises relevant instance of DAO handler and returns it
    """

    db_controller = None
    sftp_connector = None

    USERS = UsersDAO
    CHATS = ChatsDAO
    SHOUTS = ShoutsDAO
    PROMPTS = PromptsDAO
    PERSONAS = PersonasDAO
    CONFIGS = ConfigsDAO

    @classmethod
    def init(cls, db_controller, sftp_connector=None):
        """Inits Singleton with specified database controller"""
        cls.db_controller = db_controller
        cls.sftp_connector = sftp_connector
