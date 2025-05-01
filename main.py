import os
import json
import time
import random
import typing
import datetime
import requests

P = typing.ParamSpec('P')
R = typing.TypeVar('R')


class Utils:
    api_link = 'http://api.onlysq.ru/ai/v2'
    stack = []
    hi_message = 'You\'ve been selected as the next AI model to handle code writing duties. Say quick hi to everyone!'

    with open('./proxies.txt', 'r', encoding='UTF-8') as file:
        proxies: list[str] = file.read().strip().split('\n')

    @staticmethod
    def get_http_proxies() -> str:
        return 'http://' + random.choice(Utils.proxies)

    @staticmethod
    def get_https_proxies() -> str:
        return 'https://' + random.choice(Utils.proxies)

    @staticmethod
    def logging(method: typing.Callable[P, str]) -> typing.Callable[P, str]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
            line = method(*args, **kwargs)
            with open('./logs.txt', 'wa', encoding='UTF-8') as file:
                file.write(datetime.datetime.now().strftime('%Y.%m.%d_%H:%M:%S') + ' | ' + line + '\n')
            return line

        return wrapper

    @staticmethod
    @logging
    def log(msg: str, *args, **kwargs) -> str:
        line = '----' * len(set(Utils.stack)) + f' Model: {ModelAggregator.model} | LOG: ' + msg.format(*args, **kwargs)
        print(line)
        return line

    @staticmethod
    @logging
    def warn(msg: str, *args, **kwargs) -> str:
        line = '----' * len(set(Utils.stack)) + f' Model: {ModelAggregator.model} | LOG: ' + msg.format(*args, **kwargs)
        print(line)
        return line

    @staticmethod
    @logging
    def error(msg: str, *args, **kwargs) -> str:
        line = '----' * len(set(Utils.stack)) + f' Model: {ModelAggregator.model} | LOG: ' + msg.format(*args, **kwargs)
        print(line)
        return line

    @staticmethod
    def logged(method: typing.Callable[P, R]) -> typing.Callable[P, R]:
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            Utils.stack.append(method)
            result = method(*args, **kwargs)
            Utils.stack.pop()
            return result

        return wrapper


class CodeAggregator:
    @staticmethod
    @Utils.logged
    def get_code(path: str) -> str | None:
        if not os.path.exists(path):
            Utils.error('File "{}" does not exist!', path)
            return None
        try:
            with open(path, 'r', encoding='UTF-8') as file:
                return file.read().strip()
        except Exception as e:
            Utils.error('Unexpected error while reading "{}" file: {}', path, e)
            return None

    @staticmethod
    @Utils.logged
    def set_code(path: str, code: str) -> bool:
        if os.path.exists(path) and not os.path.isfile(path):
            Utils.error('File "{}" is not a file!', path)
            return False
        try:
            with open(path, 'w', encoding='UTF-8') as file:
                file.write(code.strip())
        except Exception as e:
            Utils.error('Unknown error occurred while writing "{}" file: {}', path, e)
            return False
        return True


class ModelAggregator:
    proxies: dict[str: str, str: str] = {'http': Utils.get_http_proxies(), 'https': Utils.get_https_proxies()}
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

    @staticmethod
    @Utils.logged
    def next_proxies() -> None:
        ModelAggregator.proxies = {'http': Utils.get_http_proxies(), 'https': Utils.get_https_proxies()}
        Utils.log('Proxies were changed: {}', ModelAggregator.proxies)

    @staticmethod
    @Utils.logged
    def next_model() -> None:
        @Utils.logged
        def search_cycle() -> str | None:
            for model in ModelAggregator.all_models[ModelAggregator.model == ModelAggregator.all_models[0]:]:
                Utils.log('Trying to get response from {}...', model)
                ModelAggregator.model = model
                send = {'model': model, 'request': {'messages': [{'role': 'user', 'content': Utils.hi_message}]}}
                response_ = requests.post(Utils.api_link, json=send)
                if response_.status_code != 200:
                    Utils.warn('Response has invalid status code {}', response_.status_code)
                    continue
                try:
                    response_ = response_.json()['choices'][0]['message']['content']
                except Exception as e:
                    Utils.warn('Response has invalid format: {}', e)
                    continue
                return response_
            return None

        Utils.log('Selecting new model...')
        while True:
            response = search_cycle()
            if isinstance(response, str):
                break
        Utils.log('New model was selected: "{}"!', response)
        time.sleep(5)

    @staticmethod
    @Utils.logged
    def ask(messages: list[dict[str: str]]) -> str:
        send = {'model': ModelAggregator.model, 'request': {'messages': messages}}
        response = ''
        while True:
            try:
                Utils.log('Trying to ask model...')
                response = requests.post(Utils.api_link, json=send, proxies=ModelAggregator.proxies, timeout=1000)
            except requests.exceptions.ProxyError as e:
                Utils.warn('Proxy error. Error\'s content: {}.. Changing proxies and trying again...', e)
                ModelAggregator.next_proxies()
                continue
            except ConnectionError as e:
                Utils.warn('Connection error. Error\'s content: {}. Trying again...', e)
                continue
            except requests.exceptions.Timeout as e:
                Utils.warn('Request timeout. Error\'s content: {}. Trying again...', e)
                continue
            except Exception as e:
                Utils.warn('Unexpected error. Error\'s content: {}. Trying again...', e)
                continue
            if not response:
                Utils.warn('There is no response. Switching models and trying again...')
                ModelAggregator.next_model()
                continue
            if response.status_code != 200:
                Utils.warn('Invalid status code: {}. Switching models and trying again...', response.status_code)
                ModelAggregator.next_model()
                continue
            try:
                response = response.json()['choices'][0]['message']['content']
            except Exception as e:
                Utils.warn('Incorrect response format: {}', e)
                Utils.warn('Response\'s content: {}', response.text)
                continue
        Utils.log('Response has been received successfully!')
        return response
