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
import uuid

from neon_utils import LOG

from config import Configuration
from migration_scripts.constants import MigrationFiles
from migration_scripts.conversations import migrate_conversations
from migration_scripts.shouts import migrate_shouts
from migration_scripts.utils import setup_db_connectors
from migration_scripts import migrate_users


def main(migration_id: str = None, dump_dir=os.getcwd(), time_since: int = 1677829600):
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

    LOG.info(f'Considered time since: {time_since}')

    config_source_files = [os.environ.get('CONFIG_PATH', 'config.json'), os.environ.get('SSH_CONFIG', None)]

    configuration = Configuration(from_files=config_source_files)

    mysql_connector, mongo_connector = setup_db_connectors(configuration=configuration,
                                                           old_db_key=os.environ.get('OLD_DB_KEY', None),
                                                           new_db_key=os.environ.get('NEW_DB_KEY', None))

    LOG.info('Established connections with dbs')

    if all(os.path.exists(os.path.join(considered_path, f.value)) for f in (MigrationFiles.NICK_MAPPING,
                                                                            MigrationFiles.CIDS,
                                                                            MigrationFiles.NICKS)):
        LOG.info('Skipping conversations migrations')

        with open(os.path.join(considered_path, MigrationFiles.NICK_MAPPING.value)) as f:
            nick_to_uuid_mapping = json.load(f)

        with open(os.path.join(considered_path, MigrationFiles.NICKS.value)) as f:
            nicks_to_consider = [x.strip() for x in f.readlines()]

        with open(os.path.join(considered_path, MigrationFiles.CIDS.value)) as f:
            cids = [x.strip() for x in f.readlines()]
    else:
        LOG.info('Starting conversations migration')
        cids, nick_to_uuid_mapping, nicks_to_consider = migrate_conversations(old_db_controller=mysql_connector,
                                                                              new_db_controller=mongo_connector,
                                                                              time_since=time_since)

        with open(os.path.join(considered_path, MigrationFiles.NICK_MAPPING.value), 'w', encoding="utf-8") as f:
            json.dump(nick_to_uuid_mapping, f)
            LOG.info(f'Stored nicks mapping in {MigrationFiles.NICK_MAPPING.value}')

        if nicks_to_consider:
            with open(os.path.join(considered_path, MigrationFiles.NICKS.value), 'w', encoding="utf-8") as f:
                nicks = [str(nick) + '\n' for nick in nicks_to_consider]
                f.writelines(nicks)
                LOG.info(f'Stored nicks list in {MigrationFiles.NICKS.value}')

        if cids:
            with open(os.path.join(considered_path, MigrationFiles.CIDS.value), 'w', encoding="utf-8") as f:
                cids = [str(cid) + '\n' for cid in cids]
                f.writelines(cids)
                LOG.info(f'Stored cid list in {MigrationFiles.CIDS.value}')

    migrate_users(old_db_controller=mysql_connector,
                  new_db_controller=mongo_connector,
                  nick_to_uuid_mapping=nick_to_uuid_mapping,
                  nicks_to_consider=nicks_to_consider)

    migrate_shouts(old_db_controller=mysql_connector,
                   new_db_controller=mongo_connector,
                   nick_to_uuid_mapping=nick_to_uuid_mapping,
                   from_cids=cids)


if __name__ == '__main__':
    main()
