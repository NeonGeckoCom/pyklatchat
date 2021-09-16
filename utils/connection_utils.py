from sshtunnel import SSHTunnelForwarder


def create_ssh_tunnel(server_address: str, username: str, password: str,
                      remote_bind_address: tuple = ('127.0.0.1', 8080)) -> SSHTunnelForwarder:
    """
        Creates tunneled SSH connection to dedicated address

        :param server_address: ssh server address
        :param username: server username
        :param password: server password
        :param remote_bind_address: remote address to bind to
    """
    server = SSHTunnelForwarder(
        server_address,
        ssh_username=username,
        ssh_password=password,
        remote_bind_address=remote_bind_address
    )
    server.start()
    return server
