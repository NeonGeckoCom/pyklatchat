# PyKlatchat

PyKlatchat is a pythonic version of [klatchat](https://github.com/NeonGeckoCom/klatchat) that is developed to make existing solution more modular and extendable.

## White Paper

An actual description of proposed solution can be found [under this link](https://github.com/NeonGeckoCom/pyklatchat/blob/master/PyKlatchat%20Whitepaper.pdf).

## Configuration

Any configuration properties should be grouped by runtime environment which is set via environment variable "<b>ENV</b>"

### Chat Server

For chat server configuration location is managed via environment variable "<b>CHATSERVER_CONFIG</b>"

#### Example of configuration

Example of configuration can be found in "chat_server/example_server_config.json"

#### Launching

Chat Server can be launched as python module from root directory: ```python -m chat_server```

### Chat Client

For chat client configuration location is managed via environment variable "<b>CHATCLIENT_CONFIG</b>"

#### Client-side configuration

Client side configuration is used to determine Javascript configs, it should be named "runtime_config.json" and placed to "chat_client/static/js"

Example can be found in "chat_client/static/js/example_runtime_config.json"


#### Server-side configuration

Example of configuration can be found in "chat_client/example_client_config.json"

#### Launching

Chat Client can be launched as python module from root directory: ```python -m chat_client```

