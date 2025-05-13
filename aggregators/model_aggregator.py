from utils import get_http_proxies, get_https_proxies, logged, log, wrn
import requests
from config import api_link, hi_message
from time import sleep

proxies: dict[str: str, str: str] = {'http': get_http_proxies(), 'https': get_https_proxies()}
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


@logged
def next_proxies() -> None:
    proxies = {'http': get_http_proxies(), 'https': get_https_proxies()}
    log('Proxies were changed: {}', proxies)


@logged
def next_model() -> None:
    @logged
    def search_cycle() -> str | None:
        for model in all_models[model == all_models[0]:]:
            log('Trying to get response from {}...', model)
            model = model
            send = {'model': model, 'request': {'messages': [{'role': 'user', 'content': hi_message}]}}
            response_ = requests.post(api_link, json=send)
            if response_.status_code != 200:
                wrn('Response has invalid status code {}', response_.status_code)
                continue
            try:
                response_ = response_.json()['choices'][0]['message']['content']
            except Exception as e:
                wrn('Response has invalid format: {}', e)
                continue
            return response_
        return None

    log('Selecting new model...')
    while True:
        response = search_cycle()
        if isinstance(response, str):
            break
    log('New model was selected: "{}"!', response)
    sleep(5)


@logged
def ask(messages: list[dict[str: str]], what: str = None) -> str:
    what = (' for ' + what) if what is not None else ''
    send = {'model': model, 'request': {'messages': messages}}
    response = ''
    while True:
        try:
            log(f'Trying to ask model{what}...')
            response = requests.post(api_link, json=send, proxies=proxies, timeout=1000)
        except requests.exceptions.ProxyError as e:
            wrn('Proxy error. Error\'s content: {}.. Changing proxies and trying again...', e)
            next_proxies()
            continue
        except ConnectionError as e:
            wrn('Connection error. Error\'s content: {}. Trying again...', e)
            continue
        except requests.exceptions.Timeout as e:
            wrn('Request timeout. Error\'s content: {}. Trying again...', e)
            continue
        except Exception as e:
            wrn('Unexpected error. Error\'s content: {}. Trying again...', e)
            continue
        if not response:
            wrn('There is no response. Switching models and trying again...')
            next_model()
            continue
        if response.status_code != 200:
            wrn('Invalid status code: {}. Switching models and trying again...', response.status_code)
            next_model()
            continue
        try:
            response = response.json()['choices'][0]['message']['content']
        except Exception as e:
            wrn('Incorrect response format: {}', e)
            wrn('Response\'s content: {}', response.text)
            continue
    log('Response has been received successfully!')
    return response


def simply(text: str) -> list[dict[str: str]]:
    return [{'user': 'role', 'content': text}]
