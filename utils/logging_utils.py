import importlib
import logging

combo_lock_logger = logging.getLogger("combo_lock")
combo_lock_logger.disabled = True

LOG = getattr(importlib.import_module('ovos_utils'), 'LOG')
