-- Runs against an isolated fake game; never uses the live g_game object.
return function(source)
  local now, count, calls, player_online = 1000, 10, 0, true
  local visible, events, handlers, bags = {}, {}, {}, {}
  local ball_counts, last_used, look_override = {[60001] = 4}, nil, nil
  local function corpse(id)
    return {id = id, getId = function(self) return self.id end, isLyingCorpse = function() return true end}
  end
  local tile = {getPosition = function() return {x = 1, y = 1, z = 7} end,
    getItems = function() return visible end}
  local player = {getPosition = function() return {x = 0, y = 0, z = 7} end}
  local env = setmetatable({}, {__index = _G})
  env._G = env
  env.g_clock = {millis = function() return now end}
  env.g_map = {getTiles = function() return {tile} end}
  env.modules = {game_playeractionbar = {getPlayerItemCount = function(id)
    return id == 3552 and count or (ball_counts[id] or 0)
  end}}
  env.g_game = {
    getLocalPlayer = function() if player_online then return player end end,
    getContainers = function() return bags end,
    useInventoryItemWith = function(id, target)
      assert(target:isLyingCorpse())
      last_used, calls = id, calls + 1
      if id == 3552 then count = count - 1 else ball_counts[id] = ball_counts[id] - 1 end
    end,
    look = function(item)
      local text = item.description or 'You see defeated Spearow (Vol:8).'
      if look_override then text = look_override(item) end
      if text then handlers.onTextMessage(20, text) end
    end,
  }
  env.connect = function(_, callbacks) handlers = callbacks end
  env.disconnect = function() handlers = {} end
  env.scheduleEvent = function(callback, delay)
    local event = {callback = callback, due = now + delay}
    events[#events + 1] = event
    return event
  end
  env.removeEvent = function(event) event.cancelled = true end
  local function tick()
    now = now + 200
    local current = events
    events = {}
    for _, event in ipairs(current) do
      if not event.cancelled then event.callback() end
    end
  end
  if type(source) == 'function' then
    source(env)
  else
    local chunk = assert(loadstring(source))
    setfenv(chunk, env)
    chunk()
  end
  local api = env.pokemacroAutoCatch
  visible = {corpse(4189)}
  api.start({pokemonNames = {'oDdIsH', 'Gloom'}, ballId = 3552})
  for i = 1, 8 do tick() end
  assert(calls == 1, 'same corpse must only receive one attempt')
  visible[1].id = 4301
  for i = 1, 4 do tick() end
  assert(calls == 1, 'changing the same corpse ID must not repeat the attempt')
  visible = {}; tick()
  visible = {corpse(4189)}
  for i = 1, 4 do tick() end
  assert(calls == 2, 'new corpse in the same tile must be eligible')
  visible = {corpse(4007)}
  for i = 1, 4 do tick() end
  assert(calls == 2, 'unselected species must not consume a ball')
  assert(api.status().catalog['4007'] == 'Spearow', 'species must be learned from Look')
  api.configure({pokemonNames = {'Spearow'}})
  for i = 1, 4 do tick() end
  assert(calls == 3, 'name selection must apply to a learned corpse ID')
  count = 0; visible = {corpse(4301)}
  api.configure({pokemonNames = {'Gloom'}})
  for i = 1, 4 do tick() end
  assert(not api.status().enabled and api.status().reason == 'no_balls')
  count = 10; visible = {}
  assert(not pcall(api.configure, {ballId = 60001, ballName = 'Test Ball'}), 'unrecognized ball must be rejected')
  assert(not pcall(api.discover_balls), 'detection must require an open bag')
  local function bagItem(id, amount, description)
    return {getId = function() return id end, getCount = function() return amount end,
      isStackable = function() return true end, description = description}
  end
  -- These item IDs and descriptions are synthetic; no new live IDs are assumed.
  local items = {
    bagItem(3552, 10, 'You see 10 Empty Ultra Balls.'),
    bagItem(60001, 4, 'You see 4 Empty Test Balls. It is a unique item.'),
    bagItem(60001, 4, 'You see 4 Empty Test Balls.'),
    bagItem(60002, 1, 'You see a Test Ball with a captured Pokémon.'),
    bagItem(60003, 20, 'You see 20 Max Revives.'),
    bagItem(60004, 1, 'You see an Empty Single Ball.'),
    bagItem(60005, 10, 'You see 3 Empty Wrong Balls.'),
  }
  bags = {{getItems = function() return items end}}
  local before = calls
  api.discover_balls()
  assert(not pcall(api.start, {pokemonNames = {'Gloom'}}), 'catching must wait for discovery')
  for i = 1, 50 do api.heartbeat(); tick() end
  local status = api.status()
  assert(not status.ball_discovery.active and status.ball_discovery.reason == 'complete')
  assert(status.ball_discovery.total == 6 and status.ball_discovery.found == 3, 'deduplicate ball types and reject other items')
  assert(calls == before, 'discovery must never throw a ball')
  local learned = {}
  for _, ball in ipairs(status.balls) do learned[ball.id] = ball.name end
  assert(learned[60001] == 'Test Ball' and learned[60004] == 'Single Ball', 'learn names from empty ball descriptions')
  assert(not learned[60002] and not learned[60003] and not learned[60005], 'filled balls, loot and wrong counts must be excluded')
  assert(not pcall(api.configure, {ballId = 60001, ballName = 'Ultra Ball'}), 'mismatched name and ID must be rejected')
  api.configure({ballId = 60001, ballName = 'Test Ball', pokemonNames = {'Gloom'}})
  visible = {corpse(4301)}
  api.start()
  assert(last_used == 60001 and count == 10 and ball_counts[60001] == 3, 'use selected ball without spending Ultra Balls')
  assert(not pcall(api.discover_balls), 'detection must be blocked while catching')
  ball_counts[60001] = 0; visible = {}; tick(); visible = {corpse(4301)}
  for i = 1, 4 do tick() end
  assert(not api.status().enabled and api.status().reason == 'no_balls' and count == 10, 'do not switch to Ultra when selected ball runs out')
  -- A manual Look with the same count must not be enough to learn the wrong ID.
  items = {bagItem(60006, 4, 'You see 4 Max Revives.')}
  local first = true
  look_override = function(item)
    if first then first = false; return 'You see 4 Empty Other Balls.' end
    return item.description
  end
  api.discover_balls()
  for i = 1, 12 do api.heartbeat(); tick() end
  assert(not pcall(api.configure, {ballId = 60006, ballName = 'Other Ball'}), 'confirm the name with a second Look')
  look_override = function() return nil end
  api.discover_balls(); api.cancel_ball_discovery()
  for i = 1, 12 do tick() end
  assert(not api.status().ball_discovery.active and api.status().ball_discovery.reason == 'cancelled')
  look_override = nil
  api.restore_ball_catalog({['60007'] = 'Saved Ball'})
  api.configure({ballId = 60007, ballName = 'Saved Ball'})
  assert(api.status().config.ballName == 'Saved Ball', 'saved ball catalog can be reused after connecting')
  count = 10; visible = {}
  api.start({ballId = 3552, ballName = 'Ultra Ball', pokemonNames = {'Gloom'}})
  now = now + 13000; tick()
  assert(not api.status().enabled and api.status().reason == 'connection_lost')
  api.start({pokemonNames = {'Gloom'}})
  player_online = false; tick()
  assert(not api.status().enabled and api.status().reason == 'offline')
  api.shutdown()
  return {passed = true, cases = 20, attempts = calls}
end
