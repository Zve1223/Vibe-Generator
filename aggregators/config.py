import os
import sys
from pathlib import Path
import configparser

all_models = [
    'gpt-4o',  # Лучшая в коде, поддержка больших проектов
    'deepseek-v3',  # Новая версия DeepSeek с улучшенной кодогенерацией
    'gpt-4-turbo',  # Оптимизированная версия GPT-4 для кода
    'gpt-4',  # Проверенная модель для сложных проектов
    'claude-3.5-sonnet',  # Сильная в логике и анализе кода
    'deepseek-r1',  # Специализирована на код, эффективная
    'llama-3.3',  # Улучшенная версия с хорошей кодогенерацией
    'llama-3.1',  # Базовая версия, но сильнее остальных ниже
    'qwen-2.5-32b',  # Улучшенная версия Qwen для сложных задач
    'claude-3-haiku',  # Быстрая, но менее мощная чем Sonnet
    'mistral',  # Компактная, но уступает в качестве кода
    'gpt-4o-mini',  # Облегчённая, подходит для мелких задач
]

# Config loading
config_path = Path(sys.argv[0]).parent / 'config.ini'
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
check_value('model', 'auto')

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
if general['DEFAULT']['MODEL'] not in all_models and general['DEFAULT']['MODEL'] != 'auto':
    general['DEFAULT']['MODEL'] = 'auto'

with open(config_path, 'w', encoding='UTF-8') as file:
    general.write(file)

if not os.path.isabs(general['DEFAULT']['SYSTEM_LOG']):
    general['DEFAULT']['SYSTEM_LOG'] = str(main_path / general['DEFAULT']['SYSTEM_LOG'])
if not os.path.isabs(general['DEFAULT']['ANSWER_LOG']):
    general['DEFAULT']['ANSWER_LOG'] = str(main_path / general['DEFAULT']['ANSWER_LOG'])
if not os.path.isabs(general['DEFAULT']['PROXIES']):
    general['DEFAULT']['PROXIES'] = str(main_path / general['DEFAULT']['PROXIES'])
if not os.path.exists(general['DEFAULT']['PROXIES']) or not os.path.isfile(general['DEFAULT']['PROXIES']):
    general['DEFAULT']['PROXIES'] = ''
if not os.path.isabs(general['DEFAULT']['PROMPTS']):
    general['DEFAULT']['PROMPTS'] = str(main_path / general['DEFAULT']['PROMPTS'])
if not os.path.isabs(general['DEFAULT']['WORKSPACE']):
    general['DEFAULT']['WORKSPACE'] = str(main_path / general['DEFAULT']['WORKSPACE'])
if not os.path.isabs(general['DEFAULT']['TASK']):
    general['DEFAULT']['TASK'] = str(main_path / general['DEFAULT']['TASK'])

if len(general.sections()) > 1:
    print('Choose section:\n  0. DEFAULT\n' + '\n'.join(f'  {i + 1}. {s}' for i, s in enumerate(general.sections())))
    answer = input('>>> ').strip()
    while not answer.isdigit() or not 0 <= int(answer) <= len(general.sections()):
        print('Wrong answer format!')
        answer = input('>>> ').strip()
    if answer == '0':
        config = general['DEFAULT']
        print('Why?.. Okay...')
    else:
        config = general[general.sections()[int(answer) - 1]]
else:
    config = general[general.sections()[0]]

compilers = ('gcc', 'clang', 'msvc')
compilers = {c: {k.split('_', 1)[1]: v for k, v in config.items() if k.startswith(c.lower() + '_')} for c in compilers}

answer_path = Path(config['ANSWER_LOG'])
workspace_path = Path(config['WORKSPACE'])
project_path = workspace_path / config['NAME']
if not answer_path.exists():
    os.mkdir(str(answer_path))
if not workspace_path.exists():
    os.mkdir(str(workspace_path))
if not project_path.exists():
    os.mkdir(str(project_path))

# For utils
api_link = 'http://api.onlysq.ru/ai/v2'
