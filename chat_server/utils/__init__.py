import os
from config import Configuration

config = Configuration(file_path=os.environ.get('CHATSERVER_CONFIG',
                                                '~/.local/share/neon/credentials.json'))

db_connector = config.get_db_controller('mongo')
