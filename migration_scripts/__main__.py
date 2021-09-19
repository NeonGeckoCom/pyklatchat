import os

from config import Configuration
from migration_scripts.conversations import migrate_conversations
from migration_scripts.utils import setup_db_connectors
from migration_scripts import migrate_users


def main():
    """Main migration scripts entry point"""
    config_source_files = [os.environ.get('CONFIG_PATH', 'config.json'), os.environ.get('SSH_CONFIG', None)]

    configuration = Configuration(from_files=config_source_files)

    mysql_connector, mongo_connector = setup_db_connectors(configuration=configuration,
                                                           old_db_key=os.environ.get('OLD_DB_KEY', None),
                                                           new_db_key=os.environ.get('NEW_DB_KEY', None))
    migrate_conversations(old_db_controller=mysql_connector, new_db_controller=mongo_connector)


if __name__ == '__main__':
    main()
