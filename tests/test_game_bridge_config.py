import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'modules/game_bridge/config.py'
spec = importlib.util.spec_from_file_location('bridge_config', path)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class GameBridgeConfigTests(unittest.TestCase):
    def test_names_are_trimmed_and_duplicates_do_not_add_attempts(self):
        result = config.normalize_config({'pokemonNames': [' Oddish ', 'oddish', 'Gloom']})
        self.assertEqual(result, {'ballId': 3552, 'ballName': 'Ultra Ball', 'catchIntervalMs': 500, 'pokemonNames': ['Oddish', 'Gloom']})

    def test_no_species_means_no_targets(self):
        self.assertEqual(config.normalize_config({'pokemonNames': []})['pokemonNames'], [])

    def test_malformed_ball_id_is_rejected(self):
        for value in [True, 0, -1, 65536, 3552.0, '3552']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.normalize_config({'ballId': value})

    def test_named_selection_is_forwarded_for_runtime_catalog_check(self):
        result = config.normalize_config({'ballId': 60001, 'ballName': ' Test Ball ', 'pokemonNames': ['Gloom']})
        self.assertEqual(result, {'ballId': 60001, 'ballName': 'Test Ball', 'catchIntervalMs': 500, 'pokemonNames': ['Gloom']})

    def test_configurable_ball_interval(self):
        self.assertEqual(config.normalize_config({'catchIntervalMs': 300})['catchIntervalMs'], 300)
        for value in [True, 99, 3001, '300', 300.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.normalize_config({'catchIntervalMs': value})

    def test_ball_requires_a_name(self):
        for value in ['', 'Revive', 'Test Ball\n', 'x' * 81 + ' Ball', 3552]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.normalize_config({'ballId': 60001, 'ballName': value})
        with self.assertRaises(ValueError):
            config.normalize_config({'ballId': 60001})

    def test_saved_catalog_ignores_malformed_entries(self):
        result = config.normalize_ball_catalog({'60001': ' Test Ball ', '0': 'Zero Ball',
            '65536': 'Huge Ball', 'True': 'Wrong Ball', '60002': 'Revive', '６０００３': 'Unicode Ball'})
        self.assertEqual(result, {'60001': 'Test Ball'})
        self.assertEqual(config.normalize_ball_catalog([]), {})

    def test_bundled_catalog_has_verified_names_for_new_users(self):
        profile = json.loads((path.parent / 'balls.json').read_text(encoding='utf-8'))
        catalog = config.normalize_ball_catalog(profile['balls'])
        self.assertEqual(len(profile['build']), 64)
        self.assertEqual(catalog, profile['balls'])
        self.assertEqual(catalog['3032'], 'Poké Ball')
        self.assertEqual(catalog['3552'], 'Ultra Ball')

    def test_malformed_species_selection_is_rejected(self):
        for value in ['Oddish', [''], [4301], ['x' * 81], ['Oddish'] * 101]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                config.normalize_config({'pokemonNames': value})


if __name__ == '__main__':
    unittest.main()
