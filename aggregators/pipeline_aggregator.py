import os
import json
from time import time as now
from aggregators.config import config
from aggregators.model_aggregator import ask, simply
from aggregators.utils import *
from aggregators.parse_aggregator import parse_qa
import translate
from aggregators.project_tree import ProjectTree


@logged
def specify_task() -> bool:
    start_time = now()
    response = ask(simply(query_context(get_prompt('Q&A'))), 'task refine')
    questions = parse_qa(response)
    if not questions or any(not i for i in questions):
        return False
    answers = []
    ru = translate.Translator('ru').translate
    for i, question in enumerate(questions):
        to_ask = f'{i + 1}/{len(questions)}. {question[0]}\n' \
                 '    0. Make the best decision possible!\n' \
                 f'    {f"{chr(10)}    ".join(f"{j}. {a}" for j, a in enumerate(question[1:], 1))}\n' \
                 f'    {len(question)}. Custom answer'
        try:
            to_translate = [i.split('. ', 1)[1] for i in to_ask.strip().split('\n')]
            to_translate = '\n'.join([to_translate[0]] + to_translate[2:-1])
            translated = ru(to_translate).split('\n')
            translated = [translated[0]] + ['Прими наилучшее решение!'] + translated[1:] + ['Пользовательский ответ']
            translated = f'{i + 1}/{len(questions)}. {translated[0]}\n' + \
                         '\n'.join(f'    {i}. {s}' for i, s in enumerate(translated[1:]))
            to_ask += '\nПеревод:\n' + translated
        except Exception as e:
            wrn('Can not translate Q&A: {}', e[:29] + '...')
        answer = input(to_ask + '\n>>> ').strip()
        while not (answer.isdigit() and 0 <= int(answer) <= len(question)):
            print(f'Wrong answer! Please, enter number between 0 and {len(question)}!')
            answer = input().strip()
        answer = int(answer)
        if answer == 0:
            answer = 'Make the best decision possible!'
        elif answer == len(question):
            answer = input('Enter your custom answer: ')
        else:
            answer = question[answer]
        answers.append(answer)
    qa = '\n'.join(f'Q: {q[0]}\nA: {a}' for q, a in zip(questions, answers))
    log('The Q&A was completed in {} seconds!', now() - start_time)
    if write_to_file('Q&A.txt', qa) is False:
        return False
    return True


@logged
def rewrite_task_for_ai() -> bool:
    response = ask(simply(query_context(get_prompt('RefineTask'))), 'task refine')
    if write_to_file('task.md', response) is False:
        return False
    return True


@logged
def get_full_project_structure() -> bool:
    response = ask(simply(query_context(get_prompt('ProjectStructure'))), 'project structure')
    if is_json(response) is False:
        return False
    if ProjectTree(json.loads(response)).has_cycle is True:
        return False
    if write_to_file('project_structure.json', response) is False:
        return False
    return True


@logged
def create_project_tree() -> bool:
    # def recursive_creator(path: str, d: dict) -> bool:
    #     status = True
    #     for key in d.keys():
    #         if isinstance(d[key], dict):
    #             if recursive_creator(os.path.join(path, key), d[key]['name']) is False:
    #                 status = False
    #         else:
    #             if write_to_file(os.path.join(path, key), '') is False:
    #                 status = False
    #     return status
#
    # project_structure = read_from_file('project_structure.json')
    # if project_structure is None:
    #     return False
    # project_structure: dict[str: list[str] | dict] = json.loads(project_structure)
    # if recursive_creator('.', project_structure) is False:
    #     return False
    create_project_structure(json.loads(read_from_file('project_structure.json')), project_path)
    return True
