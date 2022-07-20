from neon_sftp import NeonSFTPConnector


def init_sftp_connector(config):
    """ Initialise SFTP Connector based on provided configuration """
    if not config:
        raise AssertionError('No SFTP Config Detected')
    return NeonSFTPConnector(host=config.get('HOST', '127.0.0.1'),
                             username=config.get('USERNAME', 'root'),
                             passphrase=config.get('PASSWORD', ''),
                             port=int(config.get('PORT', 22)),
                             root_path=config.get('ROOT_PATH', '/'))
