"""Run the bundled bridge before importing Flask, the GUI or OCR packages."""
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
BRIDGE_ROOT = ROOT / 'modules/game_bridge'


def run_worker(arguments):
    sys.path.insert(0, str(BRIDGE_ROOT))
    sys.argv = [str(BRIDGE_ROOT / 'worker.py'), *arguments]
    runpy.run_path(str(BRIDGE_ROOT / 'worker.py'), run_name='__main__')


def self_test(destination):
    """Check the actual frozen bundle without connecting to a game."""
    try:
        import frida
        profile = json.loads((BRIDGE_ROOT / 'balls.json').read_text(encoding='utf-8'))
        for filename in ('worker.py', 'config.py', 'lua_bridge.js', 'runtime.lua'):
            if not (BRIDGE_ROOT / filename).is_file():
                raise RuntimeError(f'Missing bundled bridge resource: {filename}')
        if not (ROOT / 'tests/game_catch_runtime.lua').is_file():
            raise RuntimeError('Missing bundled runtime validation')
        if profile['build'] not in (BRIDGE_ROOT / 'lua_bridge.js').read_text(encoding='utf-8'):
            raise RuntimeError('The bundled bridge and ball catalog disagree')
        if frida.__version__ != '17.17.0':
            raise RuntimeError('Unexpected bundled Frida version')
        # Loading the local device also verifies the native Frida extension.
        device = frida.get_local_device()
        result = {'passed': True, 'frozen': bool(getattr(sys, 'frozen', False)),
                  'frida_version': frida.__version__, 'device': device.id,
                  'ball_types': len(profile['balls'])}
    except Exception as error:
        result = {'passed': False, 'error': str(error)}
    Path(destination).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    return 0 if result['passed'] else 1
