"""Elevated Frida worker with fixed Auto Catch operations and a client lease."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import threading
import time

import frida
from config import normalize_config, normalize_ball_catalog

ROOT = Path(__file__).resolve().parent
CLIENT_NAME = 'PokeAlliance_gl.exe'
BUILD = '5db2cf3f15ae5e92ea6843a8a80011723146068b409dda930387521d123f6e33'
parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--parent', type=int, required=True)
parser.add_argument('--session', required=True)
parser.add_argument('--pid', type=int)
args = parser.parse_args()
directory = args.directory.resolve()
directory.mkdir(parents=True, exist_ok=True)
session = script = None
catalog_path = directory / ('balls-' + BUILD + '.json')
try:
    saved_catalog = normalize_ball_catalog(json.loads(catalog_path.read_text(encoding='utf-8')))
except (ValueError, OSError):
    saved_catalog = {}


def write(name, data):
    global saved_catalog
    if name == 'status.json' and isinstance(data.get('balls'), list):
        catalog = normalize_ball_catalog({str(ball['id']): ball['name'] for ball in data['balls']})
        if catalog != saved_catalog:
            temporary_catalog = catalog_path.with_suffix('.tmp')
            temporary_catalog.write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
            temporary_catalog.replace(catalog_path)
            saved_catalog = catalog
    data.update(session=args.session, updated=time.time())
    target = directory / name
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    for retry in range(5):
        try:
            temporary.replace(target)
            return
        except PermissionError:
            time.sleep(0.02)
    raise RuntimeError('Could not update game bridge status')


def run(source):
    timer = threading.Timer(20, script.unload)
    timer.daemon = True
    timer.start()
    try:
        result = script.exports_sync.run(source)
    finally:
        timer.cancel()
    if result.get('bridge_error'):
        raise RuntimeError(result['bridge_error'])
    raw = result.get('result_bytes')
    text = bytes(raw).decode('utf-8') if raw is not None else None
    if result['status']:
        raise RuntimeError(text)
    return json.loads(text) if text is not None else None


def call(method, value=None):
    allowed = {'status', 'configure', 'start', 'stop', 'shutdown', 'discover_balls', 'cancel_ball_discovery'}
    if method not in allowed:
        raise ValueError('Unknown game bridge operation')
    if method in {'configure', 'start'}:
        value = normalize_config(value or {})
    argument = '' if value is None else 'json.decode(' + json.dumps(json.dumps(value, ensure_ascii=True)) + ')'
    return run(f'return json.encode(pokemacroAutoCatch.{method}({argument}))')


kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
kernel.QueryFullProcessImageNameW.restype = ctypes.c_int
parent_handle = kernel.OpenProcess(0x100000, False, args.parent)


def client_executable(pid):
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        raise RuntimeError('Windows did not allow reading the game executable path')
    try:
        size = ctypes.c_uint32(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            raise RuntimeError('Could not identify the running PokeAlliance executable')
        return Path(path.value)
    finally:
        kernel.CloseHandle(handle)

try:
    profile = json.loads((ROOT / 'balls.json').read_text(encoding='utf-8'))
    if profile.get('build') != BUILD:
        raise RuntimeError('The ball catalog does not match the verified client profile')
    # Include verified names for new users; personal discoveries extend this list.
    saved_catalog.update(normalize_ball_catalog(profile.get('balls')))
    if not parent_handle:
        raise RuntimeError('Pokemacro process is no longer running')
    device = frida.get_local_device()
    pid = args.pid
    if pid is None:
        matches = [p for p in device.enumerate_processes() if p.name.lower() == CLIENT_NAME.lower()]
        if len(matches) != 1:
            raise RuntimeError('Open one PokeAlliance client before connecting')
        pid = matches[0].pid
    executable = client_executable(pid)
    if executable.name.lower() != CLIENT_NAME.lower() or hashlib.sha256(executable.read_bytes()).hexdigest() != BUILD:
        raise RuntimeError('PokeAlliance was updated; the Lua bridge needs a new verified profile')
    session = device.attach(pid)
    script = session.create_script((ROOT / 'lua_bridge.js').read_text(encoding='utf-8'))
    script.load()
    harness_path = ROOT.parents[1] / 'tests/game_catch_runtime.lua'
    if harness_path.exists():
        harness = harness_path.read_text(encoding='utf-8')
        runtime = (ROOT / 'runtime.lua').read_text(encoding='utf-8')
        test_source = ('local harness = (function()\n' + harness + '\nend)()\n'
                      'local runtime = function(env)\n'
                      'local _G, g_game, g_map, g_clock, modules = env, env.g_game, env.g_map, env.g_clock, env.modules\n'
                      'local connect, disconnect, scheduleEvent, removeEvent = env.connect, env.disconnect, env.scheduleEvent, env.removeEvent\n'
                      + runtime + '\nend\nreturn json.encode(harness(runtime))\n')
        validation = run(test_source)
        if not validation.get('passed'):
            raise RuntimeError('Auto Catch runtime validation failed')
    snapshot = run((ROOT / 'runtime.lua').read_text(encoding='utf-8'))
    if saved_catalog:
        catalog_argument = json.dumps(json.dumps(saved_catalog, ensure_ascii=True))
        snapshot = run(f'return json.encode(pokemacroAutoCatch.restore_ball_catalog(json.decode({catalog_argument})))')
    # A fresh application connection starts with catching disabled.
    snapshot = call('stop')
    write('status.json', dict(snapshot, pid=pid, worker_pid=os.getpid()))
    last_id = None
    heartbeat = 0
    while kernel.WaitForSingleObject(parent_handle, 0) == 258:
        request_path = directory / 'request.json'
        if request_path.exists():
            try:
                request = json.loads(request_path.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                request = {}
            request_id = request.get('id')
            if request.get('session') == args.session and request_id and request_id != last_id:
                last_id = request_id
                try:
                    operation = request.get('operation')
                    if operation == 'disconnect':
                        call('shutdown')
                        write('response.json', {'id': request_id, 'ok': True, 'result': {'connected': False, 'enabled': False}})
                        break
                    snapshot = call(operation, request.get('config'))
                    write('response.json', {'id': request_id, 'ok': True, 'result': snapshot})
                    write('status.json', dict(snapshot, pid=pid, worker_pid=os.getpid()))
                except Exception as error:
                    write('response.json', {'id': request_id, 'ok': False, 'error': str(error)})
        if time.monotonic() - heartbeat >= 2:
            snapshot = run('pokemacroAutoCatch.heartbeat(12); return json.encode(pokemacroAutoCatch.status())')
            write('status.json', dict(snapshot, pid=pid, worker_pid=os.getpid()))
            heartbeat = time.monotonic()
        time.sleep(0.05)
except Exception as error:
    write('status.json', {'connected': False, 'enabled': False, 'error': str(error)})
finally:
    if script is not None:
        try:
            call('shutdown')
        except Exception:
            pass
        try:
            script.unload()
        except Exception:
            pass
    if session is not None:
        try:
            session.detach()
        except Exception:
            pass
    if parent_handle:
        kernel.CloseHandle(parent_handle)
    try:
        status = json.loads((directory / 'status.json').read_text(encoding='utf-8'))
        status.update(connected=False, enabled=False)
        write('status.json', status)
    except Exception:
        pass
