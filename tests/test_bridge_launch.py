import importlib.util
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('test_game_client', ROOT / 'modules/game_client.py')
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class BridgeLaunchTests(unittest.TestCase):
    def test_frozen_worker_reuses_the_portable_executable(self):
        executable = str(ROOT / 'Release Folder/pokemacro.exe')
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', executable):
            actual, arguments, directory = client.worker_launch()
        self.assertEqual(actual, executable)
        self.assertEqual(arguments, ['--game-bridge-worker'])
        self.assertEqual(directory, Path(executable).parent)

    def test_worker_entry_does_not_start_the_gui_or_flask(self):
        worker = Mock()
        arguments = ['--directory', 'bridge-status', '--parent', '123', '--session', 'test']
        with patch.object(sys, 'argv', ['pokemacro.exe', '--game-bridge-worker', *arguments]), \
                patch.dict(sys.modules, {'bridge_entry': SimpleNamespace(run_worker=worker), 'webview': None, 'modules': None}):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(ROOT / 'main.py'), run_name='__main__')
        self.assertEqual(result.exception.code, 0)
        worker.assert_called_once_with(arguments)


if __name__ == '__main__':
    unittest.main()
