import os
import sys
import typing
import random
import datetime
from pathlib import Path
from aggregators.config import *

P = typing.ParamSpec('P')
R = typing.TypeVar('R')

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
model = all_models[0]


def remove_recursion(s: list) -> int:
    if not s:
        return 0
    n = 1
    for i in range(1, len(s)):
        n += s[i - 1] != s[i]
    return n


def get_http_proxies() -> str:
    return ('http://' + random.choice(proxies)) if proxies_path else ''


def get_https_proxies() -> str:
    return ('https://' + random.choice(proxies)) if proxies_path else ''


stack = []

if proxies_path is not None:
    with open(proxies_path, 'r', encoding='UTF-8') as file:
        proxies: list[str] = file.read().strip().split('\n')
else:
    proxies = list[str]()

iteration = 0


def logging(method: typing.Callable[P, str]) -> typing.Callable[P, str]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        line = method(*args, **kwargs)
        with open(logs_path, 'a', encoding='UTF-8') as file:
            file.write(datetime.datetime.now().strftime('%Y.%m.%d_%H:%M:%S') + ' | ' + line + '\n')
        return line

    return wrapper


@logging
def log(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | LOG ' + '----' * remove_recursion(stack) + ' | ' + msg.format(*args, **kwargs)
    print(line)
    return line


@logging
def wrn(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | WRN ' + '----' * remove_recursion(stack) + ' | ' + msg.format(*args, **kwargs)
    print(line)
    return line


@logging
def err(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | ERR ' + '----' * remove_recursion(stack) + ' | ' + msg.format(*args, **kwargs)
    print(line)
    return line


def logged(method: typing.Callable[P, R]) -> typing.Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        log(f'Entering the "{method.__name__}" function...')
        stack.append(method)
        result = method(*args, **kwargs)
        stack.pop()
        log(f'Exit from the "{method.__name__}" function')
        return result

    return wrapper


@logged
def read_from_file(path: str, absolute: bool = False) -> str | None:
    if absolute is False:
        path = workspace_path / path
    else:
        path = Path(path)
    if not path.exists():
        err('File "{}" does not exist!', path)
        return None
    if not path.is_file():
        err('File "{}" is not a file!', path)
        return None
    try:
        with open(str(path), 'r', encoding='UTF-8') as file:
            return file.read()
    except Exception as e:
        err('Unexpected error while reading "{}" file:\n{}', path, e)
        return None


@logged
def write_to_file(path: str, content: str, absolute: bool = False, *, mode: str = 'w') -> bool:
    if absolute is False:
        path = workspace_path / path
    else:
        path = Path(path)
    if path.exists() and not path.is_file():
        err('File "{}" does not exist!', path)
        return False
    try:
        with open(path, mode, encoding='UTF-8') as file:
            file.write(content)
    except Exception as e:
        err('Unknown error occurred while writing "{}" file:\n{}', path, e)
        return False
    return True


def query_context(text: str) -> str:
    context = {}
    if '{task}' in text:
        if (project_path / 'task.md').exists():
            task = read_from_file('task.md')
        else:
            task = read_from_file(config.get('TASK'))
        if task is not None:
            context['task'] = task
        else:
            pass  # TODO: error
    if '{project_structure}' in text:
        project_structure = read_from_file('project_structure.json')
        if project_structure is not None:
            context['project_structure'] = project_structure
        else:
            pass  # TODO: error
    return text.format(**context)


def get_prompt(name: str) -> str | None:
    path = Path(sys.argv[0]).parent / 'prompts' / (name + '.txt')
    if not path.exists() or not path.is_file():
        return None
    with open(path, 'r', encoding='UTF-8') as file:
        return file.read()
