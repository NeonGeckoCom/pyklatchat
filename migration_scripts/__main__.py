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
import uuid
from enum import Enum

from neon_utils import LOG

from config import Configuration
from migration_scripts.constants import MigrationFiles
from migration_scripts.conversations import migrate_conversations
from migration_scripts.utils import setup_db_connectors
from migration_scripts import migrate_users


def main(migration_id: str = None, dump_dir=os.getcwd(), time_since: int = 1577829600):
    """
        Main migration scripts entry point

        :param migration_id: migration id to run
        :param dump_dir: directory for dumping files to
        :param time_since: timestamp since which to do a migration
    """
    migration_id = migration_id or uuid.uuid4().hex

    considered_path = os.path.join(dump_dir, 'passed_migrations', migration_id)

    if not os.path.exists(considered_path):
        os.makedirs(considered_path, exist_ok=True)

    LOG.info(f'Initiating migration id: "{migration_id}"')

    config_source_files = [os.environ.get('CONFIG_PATH', 'config.json'), os.environ.get('SSH_CONFIG', None)]

    configuration = Configuration(from_files=config_source_files)

    mysql_connector, mongo_connector = setup_db_connectors(configuration=configuration,
                                                           old_db_key=os.environ.get('OLD_DB_KEY', None),
                                                           new_db_key=os.environ.get('NEW_DB_KEY', None))

    LOG.info('Established connections with dbs')

    nick_mapping_file = 'nick_mapping.json'

    cid_list_file = 'cids.txt'

    if all(os.path.exists(os.path.join(considered_path, f.value)) for f in (MigrationFiles.NICK_MAPPING,
                                                                            MigrationFiles.CIDS,)):
        LOG.info('Skipping conversations migrations')

        with open(os.path.join(considered_path, MigrationFiles.NICK_MAPPING.value)) as f:
            nick_to_uuid_mapping = json.load(f)
    else:
        LOG.info('Starting conversations migration')
        cids, nick_to_uuid_mapping = migrate_conversations(old_db_controller=mysql_connector,
                                                           new_db_controller=mongo_connector,
                                                           time_since=time_since)

        with open(os.path.join(considered_path, nick_mapping_file), 'w') as f:
            json.dump(nick_to_uuid_mapping, f)
            LOG.info(f'Stored nicks mapping in {nick_mapping_file}')

        with open(os.path.join(considered_path, cid_list_file), 'w') as f:
            cids = [cid+'\n' for cid in cids]
            f.writelines(cids)
            LOG.info(f'Stored cid list in {cid_list_file}')

    migrate_users(old_db_controller=mysql_connector,
                  new_db_controller=mongo_connector,
                  nick_to_uuid_mapping=nick_to_uuid_mapping)


if __name__ == '__main__':
    main(migration_id='f688600fbfaa4dd098626609fb2f2f6d')
