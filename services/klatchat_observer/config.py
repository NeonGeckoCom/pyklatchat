import json
from os.path import isfile, join, dirname

from ovos_config.config import Configuration

from utils.logging_utils import LOG


def load_config() -> dict:
    """
    Load and return a configuration object,
    """
    legacy_config_path = "/app/app/config.json"
    if isfile(legacy_config_path):
        LOG.warning(f"Deprecated configuration found at {legacy_config_path}")
        with open(legacy_config_path) as f:
            config = json.load(f)
        LOG.debug(f'Loaded config - {config}')
        return config
    config = Configuration()
    if not config:
        LOG.warning(f"No configuration found! falling back to defaults")
        default_config_path = join(dirname(__file__), "default_config.json")
        with open(default_config_path) as f:
            config = json.load(f)
    return config
