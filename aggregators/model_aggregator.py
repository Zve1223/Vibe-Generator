from aggregators.utils import get_http_proxies, get_https_proxies, logged, log, wrn
from aggregators import utils
import requests
from aggregators.config import api_link, config
from time import sleep

proxies: dict[str: str, str: str] = {'http': get_http_proxies(), 'https': get_https_proxies()}


@logged
def next_proxies() -> None:
    global proxies
    proxies = {'http': get_http_proxies(), 'https': get_https_proxies()}
    log('Proxies were changed: {}', proxies)


@logged
def next_model(messages: list[dict[str: str, str: str]]) -> requests.Response:
    @logged
    def search_cycle() -> requests.Response | None:
        for model in utils.all_models[utils.context['model'] == utils.all_models[0]:]:
            utils.model = model
            log('Trying to get response from {}...', model)
            send = {'model': model, 'request': {'messages': messages}}
            response_ = requests.post(api_link, json=send)
            if response_.status_code != 200:
                wrn('Response has invalid status code {}', response_.status_code)
                continue
            try:
                response_.json()['choices'][0]['message']['content']
            except Exception as e:
                wrn('Response has invalid format: {}', e)
                continue
            return response_
        return None

    log('Selecting new model...')
    while True:
        response = search_cycle()
        if response is not None:
            break
    log('New model was selected: {}!', (response.json()['choices'][0]['message']['content'][:29] + '...').__repr__())
    return response


@logged
def ask(messages: list[dict[str: str]], what: str = None) -> str:
    what = (' for ' + what) if what is not None else ''
    send = {'model': utils.context['model'], 'request': {'messages': messages}}
    result = None
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
        try:
            result = response.json()['choices'][0]['message']['content']
        except Exception as e:
            wrn('Incorrect response format: {}', e)
            wrn('Response\'s content: {}', response.text.replace('\n', '\\n'))
            if not response:
                wrn('There is no response. Switching models and trying again...')
            elif response.status_code != 200:
                wrn('Invalid status code: {}. Switching models and trying again...', response.status_code)
            if config['MODEL'] == 'auto':
                response = next_model(messages)
            else:
                sleep(5)
                continue
            result = response.json()['choices'][0]['message']['content']
        break
    log('Response has been received successfully!')
    utils.write_answer(response.json())
    return result


def simply(text: str, *, role: str = 'user') -> list[dict[str: str]]:
    return [{'role': role, 'content': text}]
