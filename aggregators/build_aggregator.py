import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def compile_project(project_path: str,
                    compiler: str = 'auto',
                    output_name: str = 'out',
                    enable_tests: bool = True) -> Dict:
    '''
    :return: {
        'success': bool,
        'output': str,
        'errors': List[Dict],
        'warnings': List[Dict],
        'executable': str,
        'tests': {
            'total': int,
            'passed': int,
            'failed': List[Dict],
            'details': List[Dict]
        }
    }
    '''
    result = {
        'success': False,
        'output': '',
        'errors': [],
        'warnings': [],
        'executable': '',
        'tests': {
            'total': 0,
            'passed': 0,
            'failed': [],
            'details': []
        }
    }

    try:
        project_root = Path(project_path).resolve()
        build_dir = project_root / 'bin'
        build_dir.mkdir(exist_ok=True)

        sources, include_dirs = find_source_files(project_root)

        if not sources:
            raise RuntimeError('No source files found in project directory')

        compiler_info = select_compiler(compiler, sources)

        compile_cmd = build_compile_command(
            compiler_info,
            sources,
            include_dirs,
            str(build_dir / output_name)
        )

        process = subprocess.run(
            compile_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        result['output'] = process.stdout + process.stderr
        result['errors'], result['warnings'] = parse_compiler_output(process.stderr)

        result['success'] = process.returncode == 0
        if result['success']:
            result['executable'] = str(build_dir / output_name)
            if compiler_info['type'] == 'msvc':
                result['executable'] = result['executable'].removesuffix('.exe') + '.exe'

            # Запуск тестов если включены и основной проект собран
            if enable_tests:
                test_results = run_tests(project_root)
                result['tests'] = test_results

        return result
    except Exception as e:
        result['errors'].append({
            'type': 'system',
            'message': str(e),
            'file': '',
            'line': 0,
            'column': 0
        })
        return result


def find_source_files(project_root: Path) -> Tuple[List[str], List[str]]:
    source_exts = {'.c', '.cpp', '.cc', '.cxx', '.c++', '.s', '.asm'}
    header_exts = {'.h', '.hpp', '.hh', '.hxx', '.inc'}

    sources = []
    include_dirs = set()

    for root, _, files in os.walk(project_root):
        if any(i in root for i in ('build', 'test')):
            continue
        for file in files:
            path = Path(root) / file
            ext = path.suffix.lower()

            if ext in source_exts:
                sources.append(str(path))
            elif ext in header_exts:
                include_dirs.add(str(path.parent))

    return sources, list(include_dirs)


def select_compiler(compiler: str, sources: List[str]) -> Dict:
    compilers = {
        'gcc': {
            'c': 'gcc',
            'cpp': 'g++',
            'flags': ['-Wall', '-Wextra', '-pedantic']
        },
        'clang': {
            'c': 'clang',
            'cpp': 'clang++',
            'flags': ['-Wall', '-Wextra', '-Wpedantic']
        },
        'msvc': {
            'c': 'cl.exe',
            'cpp': 'cl.exe',
            'flags': ['/W4', '/EHsc', '/nologo']
        }
    }

    if compiler == 'auto':
        has_cpp = any(file.endswith(('.cpp', '.cc', '.cxx')) for file in sources)
        compiler = 'clang++' if has_cpp else 'clang'
        for key in compilers:
            if key in compiler.lower():
                compiler = key
                break
        else:
            compiler = 'gcc' if os.name != 'nt' else 'msvc'

    if compiler == 'msvc':
        vcvars = find_vcvarsall()
        if vcvars:
            # Добавьте архитектуру (x64/x86)
            compiler_env = get_msvc_env(vcvars)  # Модифицируйте get_msvc_env
            os.environ.update(compiler_env)

    return {
        'name': compiler,
        'type': 'msvc' if compiler == 'msvc' else 'gnu',
        **compilers.get(compiler, compilers['gcc'])
    }


def build_compile_command(compiler_info: Dict,
                          sources: List[str],
                          include_dirs: List[str],
                          output_path: str) -> List[str]:
    is_cpp = any(f.endswith(('.cpp', '.cc', '.cxx')) for f in sources)
    compiler = compiler_info['cpp'] if is_cpp else compiler_info['c']

    cmd = [compiler]

    cmd += compiler_info['flags']

    if compiler_info['type'] != 'msvc':
        std = '-std=c++23' if is_cpp else '-std=c11'
        cmd.append(std)
    else:
        vc_include = r"D:\Applications\Visual Studio\2022\Preview\VC\Tools\MSVC\14.44.35128\include"
        win_sdk_include = r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\ucrt"
        cmd += [
            f'/I{vc_include}',
            f'/I{win_sdk_include}',
            '/std:c++latest'  # Явно указываем стандарт
        ]

    for include in include_dirs:
        cmd.append(f'-I{include}' if compiler_info['type'] != 'msvc' else f'/I{include}')

    cmd += sources

    if compiler_info['type'] != 'msvc':
        cmd += ['-o', str(output_path)]
    else:
        cmd += [f'/Fe{output_path}']

    if compiler_info['type'] == 'msvc':
        cmd += ['/link', 'kernel32.lib', 'user32.lib']

    return cmd


def parse_compiler_output(output: str) -> Tuple[List[Dict], List[Dict]]:
    errors = []
    warnings = []

    # Объединенные паттерны для всех типов ошибок
    patterns = [
        # GCC/Clang ошибки компиляции
        re.compile(
            r'^(?P<file>.+?):'
            r'(?P<line>\d+):'
            r'(?P<column>\d+): '
            r'(?P<type>fatal error|error|warning|note): '
            r'(?P<message>.+)'
        ),
        # MSVC ошибки компиляции
        re.compile(
            r'^(?P<file>.+?)'
            r'\((?P<line>\d+),(?P<column>\d+)\): '
            r'(?P<type>error|warning) (?P<code>C\d+): '
            r'(?P<message>.+)'
        ),
        # Ошибки линковки (общие)
        re.compile(
            r'^(?P<type>LINK|ld): '
            r'(?P<message>.*)'
        ),
        # MSVC ошибки линковки
        re.compile(
            r'^(?P<file>.+?): '
            r'(?P<type>warning|fatal error) (?P<code>LNK\d+): '
            r'(?P<message>.+)'
        ),
        # GCC/Clang ошибки линковки
        re.compile(
            r'^undefined reference to `(?P<symbol>.+)\''
        )
    ]

    current_entry = None
    context_lines = []

    for line in output.split('\n'):
        line = line.strip()

        # Сбор контекста для текущей ошибки
        if current_entry:
            # Проверка на продолжение сообщения
            if any(c in line for c in ('^', '~', '>')) or line.startswith('   '):
                context_lines.append(line)
                continue
            else:
                # Фиксация собранного контекста
                current_entry['context'] = '\n'.join(context_lines)
                if 'error' in current_entry['type'].lower():
                    errors.append(current_entry)
                else:
                    warnings.append(current_entry)
                current_entry = None
                context_lines = []

        # Проверка всех паттернов
        for pattern in patterns:
            if match := pattern.search(line):
                groups = match.groupdict()
                entry = {
                    'type': groups.get('type', 'error').lower(),
                    'file': os.path.normpath(groups.get('file', '')),
                    'line': int(groups.get('line', 0)),
                    'column': int(groups.get('column', 0)),
                    'message': groups.get('message', line),
                    'code': groups.get('code', ''),
                    'context': ''
                }

                # Специфичная обработка для разных типов
                if 'LNK' in entry['code'] or 'LINK' in entry['type']:
                    entry['stage'] = 'linking'
                elif 'undefined reference' in line:
                    entry.update({
                        'type': 'error',
                        'stage': 'linking',
                        'message': f"Undefined symbol: {groups['symbol']}"
                    })

                current_entry = entry
                break

    # Фиксация последней собранной ошибки
    if current_entry:
        current_entry['context'] = '\n'.join(context_lines)
        if 'error' in current_entry['type'].lower():
            errors.append(current_entry)
        else:
            warnings.append(current_entry)

    return errors, warnings


def find_vcvarsall():
    vswhere = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio' / 'Installer' / 'vswhere.exe'
    if vswhere.exists():
        result = subprocess.run(
            [str(vswhere), '-latest', '-property', 'installationPath'],
            capture_output=True,
            text=True
        )
        vs_path = Path(result.stdout.strip())
        vcvars = vs_path / 'VC' / 'Auxiliary' / 'Build' / 'vcvarsall.bat'
        if vcvars.exists():
            return vcvars
    return None


def get_msvc_env(vcvars_path: Path):
    result = subprocess.run(
        f'"{vcvars_path}" x64 && set',
        shell=True,
        capture_output=True,
        text=True
    )
    env = {}
    for line in result.stdout.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            env[key] = value
    return env


def find_test_cases(project_root: Path) -> List[Path]:
    test_dir = project_root / 'tests'
    test_sources = []

    if test_dir.exists() and test_dir.is_dir():
        for file in test_dir.glob('**/*'):
            if file.suffix.lower() in {'.c', '.cpp', '.cc', '.cxx'}:
                test_sources.append(file)

    return test_sources


def build_test_command(compiler_info: Dict, sources: List[str], output_path: str) -> List[str]:
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


def parse_gtest_output(output: str) -> Dict:
    result = {
        'total': 0,
        'passed': 0,
        'failed': [],
        'details': []
    }

    test_case_pattern = re.compile(
        r'^\[\s*(RUN|OK|FAILED)\s*] (\w+\.\w+)'
    )

    fail_pattern = re.compile(
        r'^\[\s*FAILED\s*] (\w+\.\w+).*?(\d+ ms)'
    )

    current_test = None

    for line in output.split('\n'):
        if line.startswith('[==========]'):
            if m := re.search(r'(\d+) tests? from (\d+) test case', line):
                result['total'] = int(m.group(1))
        elif match := test_case_pattern.match(line):
            status, name = match.groups()
            current_test = {
                'name': name,
                'status': 'RUNNING',
                'errors': []
            }

        elif line.startswith('error:'):
            if current_test:
                current_test['errors'].append(line.strip())

        elif match := fail_pattern.match(line):
            name, duration = match.groups()
            result['failed'].append({
                'name': name,
                'duration': duration,
                'output': line.strip()
            })
            result['details'].append(current_test)
            current_test = None

        elif 'PASSED' in line:
            result['passed'] += 1
            if current_test:
                current_test['status'] = 'PASSED'
                result['details'].append(current_test)
                current_test = None

    return result


def compile_and_run_test(test_source: Path) -> Dict:
    test_result = {
        'name': test_source.name,
        'success': False,
        'output': '',
        'errors': [],
        'gtest_results': {},
        'executable': '',
        'exit_code': -1
    }

    try:
        build_dir = test_source.parent / 'build'
        build_dir.mkdir(exist_ok=True)
        compile_cmd = build_test_command(
            select_compiler('msvc', os.listdir(test_source.parent)),
            [str(test_source)],
            str(build_dir / 'gtest_test')
        )
        process = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if process.returncode != 0:
            full_output = process.stdout + "\n" + process.stderr
            print(full_output)
            test_result['errors'], test_result['warnings'] = parse_compiler_output(full_output)
            return test_result
        test_exe = build_dir / 'gtest_test'
        test_result['executable'] = str(test_exe)
        run_process = subprocess.run(
            [str(test_exe), '--gtest_brief=1'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        gtest_results = parse_gtest_output(run_process.stdout)
        test_result.update({
            'success': run_process.returncode == 0 and len(gtest_results['failed']) == 0,
            'output': run_process.stdout + run_process.stderr,
            'exit_code': run_process.returncode,
            'gtest_results': gtest_results
        })
    except Exception as e:
        test_result['errors'].append({
            'type': 'system',
            'message': str(e),
            'file': str(test_source),
            'line': 0,
            'column': 0
        })

    return test_result


def run_tests(project_root: Path) -> Dict:
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


if __name__ == '__main__':
    result = compile_project(
        r'D:\C++ Projects\labwork9-Zve1223',
        compiler='clang',
        output_name='a.exe',
        enable_tests=True
    )

    # print(json.dumps(result, indent=4, ensure_ascii=False))
    if result['success']:
        print(f"Build successful! Tests passed: {result['tests']['passed']}/{result['tests']['total']}")
        for failed_test in result['tests']['failed']:
            print(f"Failed test: {failed_test['test']}")
            print(f'{json.dumps(result, indent=4, ensure_ascii=False)}')
    else:
        print("Build failed!")
