import aggregators


if __name__ == '__main__':
    aggregators.utils.log('PROGRAMME STARTED')
    try:
        aggregators.pipeline.specify_task()
        aggregators.pipeline.rewrite_task_for_ai()
        aggregators.pipeline.get_full_project_structure()
    except Exception as e:
        aggregators.utils.err('FATAL ERROR: {}', e)
    finally:
        aggregators.utils.stack.clear()
        aggregators.utils.log('PROGRAMME FINISHED')
