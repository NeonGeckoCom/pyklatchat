import os
from config import Configuration

config_file_path = os.environ.get('CHATSERVER_CONFIG', '~/.local/share/neon/credentials.json')
server_env = os.environ.get('SERVER_ENV', 'LOCALHOST')

config = Configuration(file_path=config_file_path)

app_config = config.config_data.get('CHAT_SERVER', {}).get('SERVER_ENV', 'LOCALHOST')
db_connector = config.get_db_controller('mongo')
