from aggregators.utils import get_http_proxies, get_https_proxies, logged, log, wrn
from aggregators import utils
import requests
from aggregators.config import api_link, hi_message
from time import sleep

proxies: dict[str: str, str: str] = {'http': get_http_proxies(), 'https': get_https_proxies()}


@logged
def next_proxies() -> None:
    proxies = {'http': get_http_proxies(), 'https': get_https_proxies()}
    log('Proxies were changed: {}', proxies)


@logged
def next_model() -> None:
    @logged
    def search_cycle() -> str | None:
        for model in utils.all_models[utils.model == utils.all_models[0]:]:
            utils.model = model
            log('Trying to get response from {}...', model)
            send = {'model': model, 'request': {'messages': [{'role': 'user', 'content': hi_message}]}}
            response_ = requests.post(api_link, json=send)
            import json
            try:
                print(json.dumps(response_.json(), indent=4, ensure_ascii=False))
            except Exception as e:
                print(e)
                print(response_.content)
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
    log('New model was selected: "{}"!', response.__repr__())


@logged
def ask(messages: list[dict[str: str]], what: str = None) -> str:
    what = (' for ' + what) if what is not None else ''
    send = {'model': utils.model, 'request': {'messages': messages}}
    response = None
    while True:
        try:
            log(f'Trying to ask model{what}...')
            response = requests.post(api_link, json=send, proxies=proxies, timeout=1000)
        except requests.exceptions.ProxyError as e:
            wrn('Proxy error. Error\'s content: {}. Changing proxies and trying again...', e)
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
            print(response.content)
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


def simply(text: str, *, role: str = 'user') -> list[dict[str: str]]:
    return [{'role': role, 'content': text}]
