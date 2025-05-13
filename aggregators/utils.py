import os.path
import typing
import random
import datetime
from config import proxies_path, logs_path, config
from model_aggregator import model
from file_aggregator import read_from_file

P = typing.ParamSpec('P')
R = typing.TypeVar('R')


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
    line = '----' * remove_recursion(stack) + f' Model: {model} | LOG: ' + msg.format(*args, **kwargs)
    print(line)
    return line


@logging
def wrn(msg: str, *args, **kwargs) -> str:
    line = '----' * remove_recursion(stack) + f' Model: {model} | WRN: ' + msg.format(*args, **kwargs)
    print(line)
    return line


@logging
def err(msg: str, *args, **kwargs) -> str:
    line = '----' * remove_recursion(stack) + f' Model: {model} | ERR: ' + msg.format(*args, **kwargs)
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


def get_project_path() -> str:
    return os.path.normpath(os.path.abspath(
        os.path.join(config.get('PROJECT.paths', {}).get('WORKSPACE', '../workspace'),
                     config.get('PROJECT.vars', {}).get('NAME', 'unnamed_project'))))


def query_context(text: str) -> str:
    context = {}
    if '{task}' in text:
        if os.path.join(get_project_path(), 'task.md'):
            task = read_from_file(get_project_path(), 'task.md')
        else:
            task = read_from_file(config.get('PROJECT.paths', {}).get('TASK', '.'))
        if task is not None:
            context['task'] = task
        # TODO: error
    if '{project_structure}' in text:
        project_structure = read_from_file('project_structure.json')
        if project_structure is not None:
            context['project_structure'] = project_structure
        # TODO: error
    return text.format(**context)
