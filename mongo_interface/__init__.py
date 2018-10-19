from functools import partial

from mongo_interface.util.config import GenConfig

__version__ = '0.0.0'

GenConfig = partial(
    GenConfig,
    config_dir='etc',
    default_settings='default-settings.yml'
)
