"""Validate the small set of actions accepted by the elevated game worker."""

def normalize_config(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid Auto Catch configuration')
    ball_id = data.get('ballId', 3552)
    if type(ball_id) is not int or not 1 <= ball_id <= 65535:
        raise ValueError('Invalid ball selection')
    ball_name = data.get('ballName', 'Ultra Ball' if ball_id == 3552 else '')
    if not valid_ball_name(ball_name):
        raise ValueError('Detect balls in an open bag and select one by name')
    ball_name = ball_name.strip()
    names = data.get('pokemonNames', ['Oddish', 'Gloom'])
    if not isinstance(names, list) or len(names) > 100:
        raise ValueError('Invalid Pokémon selection')
    selected, seen = [], set()
    for name in names:
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise ValueError('Invalid Pokémon name')
        name = name.strip()
        if name.casefold() not in seen:
            seen.add(name.casefold())
            selected.append(name)
    # The Lua runtime also checks this pair against its discovered ball catalog.
    return {'ballId': ball_id, 'ballName': ball_name, 'pokemonNames': selected}


def valid_ball_name(name):
    return (isinstance(name, str) and 5 <= len(name.strip()) <= 80
            and name.isprintable() and name.strip().endswith(' Ball'))


def normalize_ball_catalog(data):
    """Read only mappings saved for this exact client build."""
    if not isinstance(data, dict):
        return {}
    result = {}
    for key, name in data.items():
        if isinstance(key, str) and key.isascii() and key.isdecimal():
            item_id = int(key)
            if 1 <= item_id <= 65535 and valid_ball_name(name):
                result[str(item_id)] = name.strip()
    return result
