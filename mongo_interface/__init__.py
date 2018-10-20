from functools import partial

from mongo_interface.util.config import GenConfig

__version__ = '0.0.1'

GenConfig = partial(
    GenConfig,
    config_dir='mongo_interface/etc',
    default_settings='default-settings.yml'
)
