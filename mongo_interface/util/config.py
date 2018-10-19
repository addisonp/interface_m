import os
import os.path
from collections import UserDict
import functools

import yaml


class ConfigException(Exception):
    pass


class GenConfig(UserDict):
    def __init__(self, config_dir, default_settings, config=None):
        UserDict.__init__(self)

        # Apply default settings
        default_settings_yml = os.path.join(config_dir, default_settings)
        with open(default_settings_yml, 'r') as yml_f:
            self.update(yaml.load(yml_f))

        # Apply environment settings
        if 'gen_util_config' in self and 'env_var' in self['gen_util_config']:
            config_env = self['gen_util_config']['env_var']

            env_settings_yml = os.environ.get(config_env, '')

            if env_settings_yml:

                if os.path.isabs(env_settings_yml):
                    # Absolute file
                    settings_yml = env_settings_yml
                else:
                    # Look for file in config_dir
                    settings_yml = os.path.join(config_dir, env_settings_yml)

                if os.path.isfile(settings_yml):
                    try:
                        with open(settings_yml, 'r') as yml_f:
                            self.merge_yml(yml_f)
                    except Exception as e:
                        raise ConfigException(
                            'Problem applying environment config file: {} {}'.format(settings_yml, e))
                else:
                    raise ConfigException('Environment config file does not exist: {}'.format(settings_yml))

        # Apply local settings
        if config:
            self.merge(config)

    def merge(self, config):
        '''Merge the given dictionary into this config'''

        dict_merge(self, config)

    def merge_yml(self, f_stream):
        '''Merge the given YAML stream into this config'''

        yml_d = yaml.load(f_stream)
        self.merge(yml_d)

    def to_yml(self):
        '''Return this config as a YAML string'''

        return yaml.dump(self.data, default_flow_style=False)


def dict_merge(dest, src):
    """
    Recursively merge src dictionary into dest

    Nested dictionaries are recursively traversed and merged. All other types
    are replaced. For example, no attempt is made to merge lists.

    z = reduce(dict_merge, [d1, d2, ...], initializer = {})
    """

    for key, val in src.items():
        if key in dest and isinstance(dest[key], dict) and isinstance(val, dict):
            dict_merge(dest[key], val)
        else:
            dest[key] = val

    return dest


def dict_reduce(dict_list, dict_merge_func=dict_merge):
    """
    Reduce the list of dictionaries, returns the accmulated result.

    Does not modify any of the dictionaries in the list.
    """

    return functools.reduce(dict_merge_func, dict_list, {})
