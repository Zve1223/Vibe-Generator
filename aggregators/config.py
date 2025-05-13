import os
from pathlib import Path
import configparser

# Config loading
config_path = r'..\settings.config'
config = {}
if not os.path.exists(config_path):
    print('ERROR: config does not exists')
elif not os.path.isfile(config_path):
    print('ERROR: config is not a file')
else:
    try:
        config = configparser.ConfigParser().read(config_path)
    except Exception as e:
        print('ERROR:', e)

# Compilers dictionary info
comp_prefix = 'COMPILER.'
compilers = (key.removeprefix(comp_prefix) for key in config.keys() if key.startswith(comp_prefix) and len(key) > 9)
compilers = {name: config[comp_prefix + name] for name in compilers}

# For utils
api_link = 'http://api.onlysq.ru/ai/v2'
hi_message = 'You\'ve been selected as the next AI model to handle code writing duties. Say quick hi to everyone!'
logs_path = '../logs.txt'
proxies_path = '../proxies.txt'
proxies_path = proxies_path if Path(proxies_path).exists() else None
