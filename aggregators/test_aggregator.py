from pathlib import Path
from config import config


def find_test_cases(project_root: Path) -> list[Path]:
    test_dir = project_root / 'tests'
    test_sources = []

    if test_dir.exists() and test_dir.is_dir():
        for file in test_dir.glob('**/*'):
            if file.suffix.lower() in {'.c', '.cpp', '.cc', '.cxx'}:
                test_sources.append(file)

    return test_sources


def build_test_command(compiler_info: dict, sources: list[str], output_path: str) -> list[str]:
    is_cpp = any(f.endswith(('.cpp', '.cc', '.cxx')) for f in sources)
    compiler = compiler_info['cpp'] if is_cpp else compiler_info['c']

    cmd = [compiler]
    cmd += compiler_info['flags']

    # Пути к GTest (измените на свои!)
    GTEST_INCLUDE_DIR = "C:/includes/googletest/include"
    GTEST_LIB_DIR = "C:/includes/googletest/lib"

    if compiler_info['type'] == 'msvc':
        # Стандартные пути MSVC (проверьте актуальность!)
        vc_include = r"D:\Applications\Visual Studio\2022\Preview\VC\Tools\MSVC\14.44.35128\include"
        win_sdk_include = r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt"
        cmd += [
            '/MT',
            f'/I{GTEST_INCLUDE_DIR}',
            f'/I{vc_include}',
            f'/I{win_sdk_include}',
            '/std:c++latest',
            '/EHsc',
            '/nologo',
            *sources,  # Исходные файлы должны быть здесь!
            f'/Fe{output_path}',
            '/link',  # Разделитель для линкера
            f'/LIBPATH:{GTEST_LIB_DIR}',
            'gtest.lib',
            'gtest_main.lib'
        ]
    else:
        cmd += [
            f'-I{GTEST_INCLUDE_DIR}',
            f'-L{GTEST_LIB_DIR}',
            '-lgtest',
            '-lgtest_main',
            '-pthread',
            '-std=c++23',
            *sources,
            '-o', output_path
        ]

    return cmd


def compile_and_run_test(test_source: Path) -> dict:
    test_result = {
        'name': test_source.name,
        'success': False,
        'output': '',
        'errors': [],
        'gtest_results': {},
        'executable': '',
        'exit_code': -1
    }

    # TODO: Complete
    # try:
    #     build_dir = test_source.parent / 'build'
    #     build_dir.mkdir(exist_ok=True)
    #     compile_cmd = build_test_command(
    #         select_compiler('msvc', os.listdir(test_source.parent)),
    #         [str(test_source)],
    #         str(build_dir / 'gtest_test')
    #     )
    #     process = subprocess.run(
    #         compile_cmd,
    #         capture_output=True,
    #         text=True,
    #         encoding='utf-8',
    #         errors='replace'
    #     )
    #     if process.returncode != 0:
    #         full_output = process.stdout + "\n" + process.stderr
    #         print(full_output)
    #         test_result['errors'], test_result['warnings'] = parse_compiler_output(full_output)
    #         return test_result
    #     test_exe = build_dir / 'gtest_test'
    #     test_result['executable'] = str(test_exe)
    #     run_process = subprocess.run(
    #         [str(test_exe), '--gtest_brief=1'],
    #         capture_output=True,
    #         text=True,
    #         encoding='utf-8'
    #     )
    #     gtest_results = parse_gtest_output(run_process.stdout)
    #     test_result.update({
    #         'success': run_process.returncode == 0 and len(gtest_results['failed']) == 0,
    #         'output': run_process.stdout + run_process.stderr,
    #         'exit_code': run_process.returncode,
    #         'gtest_results': gtest_results
    #     })
    # except Exception as e:
    #     test_result['errors'].append({
    #         'type': 'system',
    #         'message': str(e),
    #         'file': str(test_source),
    #         'line': 0,
    #         'column': 0
    #     })

    return test_result


def run_tests(project_root: Path) -> dict:
    test_results = {
        'total': 0,
        'passed': 0,
        'failed': [],
        'details': []
    }

    test_sources = find_test_cases(project_root)

    for test_source in test_sources:
        test_result = compile_and_run_test(test_source)
        test_results['details'].append(test_result)

        if test_result['success']:
            test_results['passed'] += 1
        else:
            test_results['failed'].append({
                'test': test_source.name,
                'output': test_result['output'],
                'errors': test_result['errors'],
                'gtest_failures': test_result['gtest_results'].get('failed', [])
            })

    test_results['total'] = len(test_sources)
    return test_results