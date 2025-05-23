import json
import traceback
import typing
import random
import datetime
from aggregators.config import *
from aggregators.project_tree import *

P = typing.ParamSpec('P')
R = typing.TypeVar('R')

context: dict[str: str | ProjectTree | dict] = {
    'task': config['TASK'],
    'model': all_models[0] if config['MODEL'] == 'auto' else config['MODEL']
}


def is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        return False


def get_ext(is_header: bool, is_template: bool) -> str:
    if is_header is True:
        return '.hpp'
    elif is_template is True:
        return '.ipp'
    else:
        return '.cpp'


def get_http_proxies() -> str:
    return ('http://' + random.choice(context['proxies'])) if config['PROXIES'] else ''


def get_https_proxies() -> str:
    return ('https://' + random.choice(context['proxies'])) if config['PROXIES'] else ''


stack = []

if config['PROXIES']:
    with open(config['PROXIES'], 'r', encoding='UTF-8') as file:
        _: list[str] = file.read().strip().split('\n')
else:
    _ = list[str]()
context['proxies'] = _

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
    model, msg = context['model'], msg.format(*args, **kwargs).strip()
    line = f'{model:<17} | LOG ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg
    print(line)
    return line


@logging
def wrn(msg: str, *args, **kwargs) -> str:
    model, msg = context['model'], msg.format(*args, **kwargs).strip()
    line = f'{model:<17} | WRN ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg
    print(line)
    return line


@logging
def err(msg: str, *args, e: Exception = None, **kwargs) -> str:
    if e is not None:
        traceback.print_exception(e)
    model, msg = context['model'], msg.format(*args, **kwargs).strip()
    line = f'{model:<17} | ERR ' + ('---+' * remove_recursion(stack))[:-1] + '| ' + msg
    print(line)
    return line


def logged(method: typing.Callable[P, R]) -> typing.Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            log(f'Entering the "{method.__name__}" function...')
            stack.append(method)
            result = method(*args, **kwargs)
        except Exception as e:
            raise e
        finally:
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
        err('Unexpected error while reading "{}" file:\n{}', path, e, e=e)
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
        err('Unknown error occurred while writing "{}" file:\n{}', path, e, e=e)
        return False
    return True


@logged
def create_project_structure(project_config: dict, root_dir: str = '.') -> None:
    project_root = Path(root_dir)
    project_root.mkdir(parents=True, exist_ok=True)
    for module in project_config['project']['modules']:
        module_dir = project_root / module['name']
        module_dir.mkdir(exist_ok=True)
        for file_info in module['files']:
            file_path = module_dir / file_info['name']
            if file_info['is_template'] is True:
                file_path.with_suffix('.tpp').touch()
            else:
                file_path.with_suffix('.hpp').touch()
                file_path.with_suffix('.cpp').touch()


def query_context(text: str) -> str:
    if '{task}' in text:
        task = read_from_file(context['task'])
        if task is not None:
            text = text.replace('{task}', task)
        else:
            pass  # TODO: error
    if '{QnA}' in text:
        QnA = read_from_file('Q&A.md')
        if QnA is not None:
            text = text.replace('{QnA}', QnA)
        else:
            pass  # TODO: error
    if '{project_structure}' in text:
        project_structure = json.dumps(context['project_structure'])
        if project_structure is not None:
            text = text.replace('{project_structure}', project_structure)
        else:
            pass  # TODO: error
    if '{target_file}' in text:
        text = text.replace('{target_file}', context['current_file'])
    if '{realization_instruction}' in text:
        name: str = context['current_file']
        node: FileNode = context['current_node']
        path = Path(node.module) / name
        realization_instruction = read_from_file(str((project_path / path).with_suffix('.md')))
        if realization_instruction is not None:
            text = text.replace('{realization_instruction}', realization_instruction)
        else:
            pass  # TODO: error
    if '{dependencies}' in text:
        project_tree: ProjectTree = context['project_tree']
        name: str = context['current_node'].name
        dependencies = project_tree.get_subtree(name)[::-1]
        if not dependencies:
            text = text.replace('{dependencies}', '')
        else:
            codes = list[str]()
            for file in dependencies:
                name = file.name + '.hpp'
                path = Path(file.module) / name
                code = read_from_file(str(project_path / path))
                if code is not None:
                    codes.append(code)
                else:
                    codes.append('')  # TODO: error
            result = '## Dependencies\n'
            for file, code in zip(dependencies, codes):
                result += f'### {file.module}/{file.name}.hpp\n```cpp\n{code.strip()}\n```\n'
            text = text.replace('{dependencies}', result)
    return text


def prompt(name: str) -> str | None:
    path = Path(sys.argv[0]).parent / 'prompts' / (name + '.md')
    if not path.exists() or not path.is_file():
        return None
    with open(path, 'r', encoding='UTF-8') as file:
        return query_context(file.read())


@logged
def write_answer(response: dict[str]) -> bool:
    if 'id' not in response.keys():
        wrn('There is no "id" in response to identify the answer')
        return False
    path = os.path.join(config['ANSWER_LOG'], response['id'].removeprefix('chat_') + '.txt')
    try:
        to_save = f'''
CREATED: {response['created']}
MODEL: {response['model']}
PROMPT: {response['usage']['prompt_tokens']}
COMPLETION: {response['usage']['completion_tokens']}
REASON: {response['choices'][0]['finish_reason']}
ROLE: {response['choices'][0]['message']['role']}
MESSAGES:
```
{response['choices'][0]['message']['content']}
```
'''.strip()
    except Exception as e:
        wrn('can not write answer in common format: {}', e)
        traceback.print_exc()
        to_save = json.dumps(response, indent=4, ensure_ascii=False)
    if write_to_file(path, to_save) is False:
        return False
    log('Answer "{}" was saved successfully!', response['id'].removeprefix('chat_'))
    return True
