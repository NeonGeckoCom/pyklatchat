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

from config import Configuration
from utils.connection_utils import create_ssh_tunnel


def setup_db_connectors(configuration: Configuration, old_db_key: str, new_db_key: str):
    """
        Migrating users from old database to new one
        :param configuration: active configuration
        :param old_db_key: old database key
        :param new_db_key: new database key
    """
    ssh_configs = configuration.config_data.get('SSH_CONFIG')
    tunnel_connection = create_ssh_tunnel(server_address=ssh_configs['ADDRESS'],
                                          username=ssh_configs['USER'],
                                          password=ssh_configs['PASSWORD'],
                                          remote_bind_address=('127.0.0.1', 3306))
    mysql_connector = configuration.get_db_controller(name=old_db_key,
                                                      override_args={'port': tunnel_connection.local_bind_address[1]})
    mongo_connector = configuration.get_db_controller(name=new_db_key)
    return mysql_connector, mongo_connector
