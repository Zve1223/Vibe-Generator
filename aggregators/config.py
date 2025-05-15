import os
import sys
from pathlib import Path
import configparser

# Config loading
config_path = Path(sys.argv[0]).parent / 'settings.config'
general = configparser.ConfigParser()
general.read(config_path)


def check_value(name: str, default: str) -> bool:
    if name not in general['DEFAULT'].keys() or not general['DEFAULT'][name]:
        general['DEFAULT'][name] = default
        return False
    return True


main_path = Path(sys.argv[0]).parent

check_value('COMPILER', 'clang')
check_value('NAME', 'unnamed_project')
check_value('TESTING', 'false')

check_value('PROMPTS', str(main_path / 'prompts'))
check_value('WORKSPACE', str(main_path / 'workspace'))
_ = str(main_path / general['DEFAULT']['WORKSPACE'] / general['DEFAULT']['NAME'] / 'task.md')
check_value('TASK', _)

_ = r'C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Tools\MSVC\14.29.30133\include'
check_value('VS_INCLUDE', _)
_ = r'C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt'
check_value('WIN_SDK_INCLUDE', _)
_ = r'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
check_value('VSWHERE', _)

check_value('GTEST_INCLUDE_DIR', r'C:\includes\googletest\include')
check_value('GTEST_LIB_DIR', r'C:\includes\googletest\lib')

if general['DEFAULT']['TESTING'] not in {'false', 'true'}:
    general['DEFAULT']['TESTING'] = 'false'
if not os.path.isabs(general['DEFAULT']['PROMPTS']):
    general['DEFAULT']['PROMPTS'] = str(main_path / general['DEFAULT']['PROMPTS'])
if not os.path.isabs(general['DEFAULT']['WORKSPACE']):
    general['DEFAULT']['WORKSPACE'] = str(main_path / general['DEFAULT']['WORKSPACE'])
if not os.path.isabs(general['DEFAULT']['TASK']):
    general['DEFAULT']['TASK'] = str(main_path / general['DEFAULT']['TASK'])

with open(config_path, 'w', encoding='UTF-8') as file:
    general.write(file)

print('Choose section:\n    0. DEFAULT\n' + '\n'.join(f'    {i + 1}. {s}' for i, s in enumerate(general.sections())))
answer = input('>>> ').strip()
while not answer.isdigit() or not 0 <= int(answer) <= len(general.sections()):
    print('Wrong answer format!')
    answer = input('>>> ').strip()
if answer == '0':
    config = general['DEFAULT']
    print('Why?.. Okay...')
else:
    config = general[general.sections()[int(answer) - 1]]

compilers = ('gcc', 'clang', 'msvc')
compilers = {c: {k.split('_', 1)[1]: v for k, v in config.items() if k.startswith(c.lower() + '_')} for c in compilers}

workspace_path = Path(config['WORKSPACE'])
project_path = workspace_path / config['NAME']
if not workspace_path.exists():
    os.mkdir(str(workspace_path))
if not project_path.exists():
    os.mkdir(str(project_path))

# For utils
api_link = 'http://api.onlysq.ru/ai/v2'
hi_message = 'You\'ve been selected as the next AI model to handle code writing duties. Say quick hi to everyone!'
logs_path = str(Path(sys.argv[0]).parent / 'logs.txt')
proxies_path = Path(sys.argv[0]).parent / 'proxies.txt'
proxies_path = str(proxies_path) if proxies_path.exists() else None
