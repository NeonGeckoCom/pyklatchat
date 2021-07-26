config_file_path = os.environ.get('CHAT_SERVER_CONFIG', '../config.json')
server_env = os.environ.get('SERVER_ENV', 'LOCALHOST')

app_config = Configuration(file_path=config_file_path).config_data.get('CHAT_SERVER', {}).get('SERVER_ENV', 'LOCALHOST')
