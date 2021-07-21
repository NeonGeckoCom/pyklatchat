config_file_path = os.environ.get('CHAT_SERVER_CONFIG', '../config.json')

app_config = Configuration(file_path=config_file_path).config_data