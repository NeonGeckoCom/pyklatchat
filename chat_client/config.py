import os
from config import Configuration

config_file_path = os.environ.get('CHATCLIENT_CONFIG', '~/.local/share/neon/credentials_client.json')
server_env = os.environ.get('APP_ENV', 'LOCALHOST')

app_config = Configuration(file_path=config_file_path).config_data.get('CHAT_CLIENT', {}).get(server_env)
