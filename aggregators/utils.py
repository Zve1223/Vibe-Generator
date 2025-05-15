import os
import sys
import json
import typing
import random
import datetime
from pathlib import Path
from aggregators.config import *

P = typing.ParamSpec('P')
R = typing.TypeVar('R')

model = all_models[0] if config['MODEL'] == 'auto' else config['MODEL']


def is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        return False


def get_http_proxies() -> str:
    return ('http://' + random.choice(proxies)) if config['PROXIES'] else ''


def get_https_proxies() -> str:
    return ('https://' + random.choice(proxies)) if config['PROXIES'] else ''


stack = []

if config['PROXIES']:
    with open(config['PROXIES'], 'r', encoding='UTF-8') as file:
        proxies: list[str] = file.read().strip().split('\n')
else:
    proxies = list[str]()

iteration = 0


def remove_recursion(s: list) -> int:
    if not s:
        return 0
    n = 1
    for i in range(1, len(s)):
        n += s[i - 1] != s[i]
    return n


def logging(method: typing.Callable[P, str]) -> typing.Callable[P, str]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        line = method(*args, **kwargs)
        with open(config['SYSTEM_LOG'], 'a', encoding='UTF-8') as file:
            file.write(datetime.datetime.now().strftime('%Y.%m.%d_%H:%M:%S') + ' | ' + line + '\n')
        return line

    return wrapper


@logging
def log(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | LOG ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg.format(*args, **kwargs).strip()
    print(line)
    return line


@logging
def wrn(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | WRN ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg.format(*args, **kwargs).strip()
    print(line)
    return line


@logging
def err(msg: str, *args, **kwargs) -> str:
    line = f'{model:<17} | ERR ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg.format(*args, **kwargs).strip()
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
    if '{QnA}' in text:
        QnA = read_from_file('Q&A.txt')
        if QnA is not None:
            context['QnA'] = QnA
        else:
            pass  # TODO: error
    if '{project_structure}' in text:
        project_structure = read_from_file('project_structure.json')
        if project_structure is not None:
            context['project_structure'] = project_structure
        else:
            pass  # TODO: error
    return text.format(**context).replace('{{', '{').replace('}}', '}')


def get_prompt(name: str) -> str | None:
    path = Path(sys.argv[0]).parent / 'prompts' / (name + '.txt')
    if not path.exists() or not path.is_file():
        return None
    with open(path, 'r', encoding='UTF-8') as file:
        return file.read()


@logged
def write_answer(response: dict[str]) -> bool:
    if 'id' not in response.keys():
        wrn('There is no "id" in response to identify the answer')
        return False
    path = os.path.join(config['ANSWER_LOG'], response['id'].removeprefix('chat_') + '.txt')
    with open(path, 'w', encoding='UTF-8') as file:
        json.dump(response, file, indent=4, ensure_ascii=False)
    log('Answer "{}" was saved successfully!', response['id'].removeprefix('chat_'))
    return True
