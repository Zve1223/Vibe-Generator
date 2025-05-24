import os
import subprocess
from pathlib import Path
from .config import config, compilers
from .parse_aggregator import parse_compiler_output


def find_vcvarsall():
    vswhere = Path(config['VSWHERE'])
    if Path(vswhere).exists():
        result = subprocess.run(
            [vswhere, '-latest', '-property', 'installationPath'],
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


def find_cpp_source_files(project_root: Path) -> tuple[list[str], list[str]]:
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


def select_cpp_compiler(compiler: str, sources: list[str]) -> dict:
    if compiler == 'auto':
        has_cpp = any(file.endswith(('.cpp', '.cc', '.cxx', '.c++')) for file in sources)
        compiler = 'clang++' if has_cpp else 'clang'
        for key in compilers.keys():
            if key in compiler.lower():
                compiler = key
                break
        else:
            compiler = 'gcc' if os.name != 'nt' else 'msvc'
    if compiler == 'msvc':
        vcvars = find_vcvarsall()
        if vcvars:
            compiler_env = get_msvc_env(vcvars)
            os.environ.update(compiler_env)
    return {
        'name': compiler,
        'type': 'msvc' if compiler == 'msvc' else 'gnu',
        **compilers.get(compiler, compilers['gcc'])
    }


def build_cpp_compile_command(compiler_info: dict,
                              sources: list[str],
                              include_dirs: list[str],
                              output_path: str) -> list[str]:
    is_cpp = any(f.endswith(('.cpp', '.cc', '.cxx')) for f in sources)
    compiler = compiler_info['cpp'] if is_cpp else compiler_info['c']

    cmd = [compiler]

    cmd += compiler_info['flags'].split()

    if compiler_info['type'] != 'msvc':
        std = f'-std={compiler_info["cpp_version"]}' if is_cpp else f'-std={compiler_info["c_version"]}'
        cmd.append(std)
    else:
        cmd += [
            f'/I{config.get("VS_INCLUDE")}',
            f'/I{config.get("WIN_SDK_INCLUDE")}',
            f'/std:{compiler["cpp_version"]}'
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


def compile_cpp_project(project_path: str, compiler: str = 'auto', output_name: str = 'out') -> dict:
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

        sources, include_dirs = find_cpp_source_files(project_root)

        if not sources:
            raise RuntimeError('No source files found in project directory')

        compiler_info = select_cpp_compiler(compiler, sources)

        compile_cmd = build_cpp_compile_command(
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
