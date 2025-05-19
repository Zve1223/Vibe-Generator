import aggregators

if __name__ == '__main__':
    aggregators.utils.log('PROGRAMME STARTED')
    try:
        # aggregators.pipeline.specify_task()
        aggregators.pipeline.rewrite_task_for_ai()
        # aggregators.pipeline.create_project_tree()
        pass
    except Exception as e:
        aggregators.utils.err('FATAL ERROR: {}', e)
    finally:
        aggregators.utils.stack.clear()
        aggregators.utils.log('PROGRAMME FINISHED')
