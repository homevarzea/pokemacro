"""Local IPC controller for the elevated, fixed-operation Frida worker."""
import atexit
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
DIRECTORY = (ROOT.parent / '.cache/game_bridge') if not getattr(sys, 'frozen', False) else Path(os.environ['APPDATA']) / 'Pokemacro/game_bridge'
_lock = threading.RLock()
_session = None
_launcher = None


def _read(name):
    try:
        return json.loads((DIRECTORY / name).read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return {}


def status():
    data = _read('status.json')
    if data.get('session') != _session or time.time() - data.get('updated', 0) > 8:
        return {'connected': False, 'enabled': False}
    return data


def worker_launch():
    if getattr(sys, 'frozen', False):
        return sys.executable, ['--game-bridge-worker'], Path(sys.executable).parent
    project_python = ROOT.parent / '.venv/Scripts/python.exe'
    interpreter = str(project_python) if project_python.exists() else sys.executable
    return interpreter, ['-B', str(ROOT / 'game_bridge/worker.py')], ROOT.parent


def connect():
    global _session, _launcher
    with _lock:
        if status().get('connected'):
            return status()
        if _launcher is not None and _launcher.poll() is None:
            raise RuntimeError('Confirm the pending Windows administrator prompt before reconnecting')
        DIRECTORY.mkdir(parents=True, exist_ok=True)
        _session = uuid.uuid4().hex
        interpreter, prefix, working_directory = worker_launch()
        worker_arguments = [
            *prefix, '--directory', str(DIRECTORY),
            '--parent', str(os.getpid()), '--session', _session,
        ]
        shell = ctypes.WinDLL('shell32', use_last_error=True)
        if shell.IsUserAnAdmin():
            launcher = subprocess.Popen([interpreter, *worker_arguments], cwd=working_directory,
                                        env={**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'},
                                        creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # Start-Process handles elevation on its own initialized Windows thread.
            # Calling ShellExecute directly on Flask's request thread can hang.
            quote = lambda value: "'" + str(value).replace("'", "''") + "'"
            command_line = ("$env:PYINSTALLER_RESET_ENVIRONMENT = '1'\nStart-Process -FilePath " + quote(interpreter)
                            + ' -ArgumentList ' + quote(subprocess.list2cmdline(worker_arguments))
                            + ' -WorkingDirectory ' + quote(working_directory)
                            + ' -Verb RunAs -WindowStyle Hidden -ErrorAction Stop')
            with (DIRECTORY / 'launcher.log').open('a', encoding='utf-8') as log:
                launcher = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command_line],
                                            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        _launcher = launcher
        # A portable worker may need to unpack the one-file bundle first.
        deadline = time.monotonic() + (60 if getattr(sys, 'frozen', False) else 25)
        while time.monotonic() < deadline:
            data = _read('status.json')
            if data.get('session') == _session:
                if data.get('error'):
                    raise RuntimeError(data['error'])
                if data.get('connected'):
                    return data
            if launcher.poll() is not None and launcher.returncode != 0:
                raise RuntimeError('Windows did not authorize the game connection as administrator')
            time.sleep(0.1)
        raise RuntimeError('The game bridge did not respond; check the Windows administrator prompt')


def command(operation, config=None):
    with _lock:
        if not status().get('connected'):
            if operation in {'stop', 'disconnect'}:
                return {'connected': False, 'enabled': False}
            connect()
        request_id = uuid.uuid4().hex
        request = {'session': _session, 'id': request_id, 'operation': operation, 'config': config}
        target = DIRECTORY / 'request.json'
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(request), encoding='utf-8')
        temporary.replace(target)
        deadline = time.monotonic() + 22
        while time.monotonic() < deadline:
            response = _read('response.json')
            if response.get('session') == _session and response.get('id') == request_id:
                if not response.get('ok'):
                    raise RuntimeError(response.get('error', 'Game bridge request failed'))
                return response.get('result')
            if not status().get('connected'):
                raise RuntimeError(status().get('error', 'Game connection was interrupted'))
            time.sleep(0.05)
        raise RuntimeError('The game bridge request timed out')


def close():
    try:
        command('disconnect')
    except Exception:
        pass


atexit.register(close)
