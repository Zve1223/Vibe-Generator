import typing
import random
import datetime
from config import proxies_path, logs_path

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
        stack.append(method)
        result = method(*args, **kwargs)
        stack.pop()
        return result

    return wrapper
