import os
import json
import traceback
from time import time as now
from typing import Callable
import shutil

import aggregators.utils
from aggregators.model_aggregator import ask, simply
from aggregators.utils import *
from aggregators.parse_aggregator import parse_qa
import translate
from aggregators.project_tree import ProjectTree


@logged
def specify_task() -> bool:
    response = ask(simply(prompt('Q&A')), 'task refine')
    questions = parse_qa(response)
    if not questions or any(not i for i in questions):
        return False
    answers = []
    ru = translate.Translator('ru').translate
    start_time = now()
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
    log('The Q&A was completed in {} seconds!', now() - start_time)
    qa = '\n'.join(f'Q: {q[0]}\nA: {a}' for q, a in zip(questions, answers))
    if write_to_file('Q&A.txt', qa) is False:
        return False
    return True


@logged
def rewrite_task_for_ai() -> bool:
    response = ask(simply(prompt('RefineTask')), 'task refine')
    if write_to_file('task.md', response) is False:
        return False
    context['task'] = 'task.md'
    return True


@logged
def create_project_tree() -> bool:
    response = ask(simply(prompt('ProjectStructure')), 'project structure')
    if is_json(response) is False:
        return False
    project_structure = json.loads(response)
    project_tree = ProjectTree(project_structure)
    if project_tree.has_cycle is True:
        return False
    context['project_structure'] = project_structure
    context['project_tree'] = project_tree
    if write_to_file('project_structure.json', response) is False:
        return False
    shutil.rmtree(project_path)
    create_project_structure(project_structure, project_path)
    return True


@logged
def write_files_instructions() -> bool:
    project_tree: ProjectTree = context['project_tree']
    for name in project_tree:
        file = project_tree[name]
        context['target_file'] = name
        response = ask(simply(prompt('FileRealizationInstruction')), 'file realization instruction writing')
        if write_to_file(str(project_path / file.path) + '.md', response) is False:
            return False




def pipeline(*pipes: Callable) -> bool:
    aggregators.utils.log('PIPELINE STARTED')
    success = True
    try:
        for n, pipe in enumerate(pipes):
            errors = {}
            while True:
                try:
                    if pipe() is False:
                        continue
                except Exception as e:
                    err('Unexpected error: {}', e)
                    errors[str(e)] = 1 if str(e) not in errors.keys() else errors[str(e)] + 1
                    if errors[str(e)] == 2:
                        raise e
                    continue
                break
    except Exception as e:
        aggregators.utils.err('FATAL ERROR: {}', e)
        traceback.print_exc()
        success = False
    finally:
        aggregators.utils.stack.clear()
        aggregators.utils.log('PIPELINE FINISHED')
        return success
