-- All map/item access and item use take place on the client's own Lua thread.
local previous
if _G.pokemacroAutoCatch then
  local ok, snapshot = pcall(_G.pokemacroAutoCatch.status)
  if ok then previous = snapshot end
  pcall(_G.pokemacroAutoCatch.shutdown)
end
local state = {enabled = false, attempts = 0, detected = 0, seen = {}, lease = 0,
  config = {ballId = 3552, ballName = 'Ultra Ball', catchIntervalMs = 500, pokemonNames = {'Oddish', 'Gloom'}},
  balls = {[3552] = 'Ultra Ball'}, discovery = {active = false, checked = 0, total = 0, found = 0},
  names = {[4189] = 'Oddish', [4301] = 'Gloom'}, last_attempt = 0, last_look = -1000}
local api = {}
_G.pokemacroAutoCatch = api

local function ballCount(id)
  id = id or state.config.ballId
  local mod = modules and modules.game_playeractionbar
  if mod and mod.getPlayerItemCount then
    local ok, count = pcall(mod.getPlayerItemCount, id)
    if ok and type(count) == 'number' then return count end
  end
  local count = 0
  for _, container in pairs(g_game.getContainers()) do
    for _, item in ipairs(container:getItems()) do
      if item:getId() == id then count = count + item:getCount() end
    end
  end
  return count
end

local function corpses()
  local player = g_game.getLocalPlayer()
  if not player then return {}, nil end
  local pos = player:getPosition()
  if not pos then return {}, nil end
  local found = {}
  for _, tile in pairs(g_map.getTiles(pos.z)) do
    local p = tile:getPosition()
    local dx, dy = math.abs(p.x - pos.x), math.abs(p.y - pos.y)
    if p.z == pos.z and dx <= 7 and dy <= 5 then
      for _, item in ipairs(tile:getItems()) do
        if item:isLyingCorpse() then
          local id = item:getId()
          found[#found + 1] = {id = id, name = state.names[id] or ('Corpse ' .. id),
            position = p, distance = math.max(dx, dy), item = item,
            key = id .. ':' .. p.x .. ':' .. p.y .. ':' .. p.z}
        end
      end
    end
  end
  table.sort(found, function(a, b) return a.distance < b.distance end)
  return found, pos
end

local function finishDiscovery(reason)
  local d = state.discovery
  d.active, d.reason = false, reason
  if d.event then removeEvent(d.event); d.event = nil end
  if state.pending_look and state.pending_look.kind == 'ball' then state.pending_look = nil end
  d.queue, d.verify_name = nil, nil
end

function api.stop(reason)
  state.enabled = false
  state.reason = reason or 'disabled'
  if state.event then removeEvent(state.event); state.event = nil end
  if state.discovery.active then finishDiscovery(state.reason) end
  state.pending_look = nil
  return api.status()
end

local function scan()
  state.event = nil
  if not state.enabled then return end
  if g_clock.millis() > state.lease then api.stop('connection_lost'); return end
  local found, pos = corpses()
  if not pos then api.stop('offline'); return end
  local present, selected = {}, {}
  for _, name in ipairs(state.config.pokemonNames) do selected[name:lower()] = true end
  for _, corpse in ipairs(found) do present[corpse.item] = true end
  for item in pairs(state.seen) do
    if not present[item] then state.seen[item] = nil end
  end
  -- Ask the server for the species only when a corpse type is still unknown.
  if not state.pending_look or g_clock.millis() - state.pending_look.at > 2000 then
    for _, corpse in ipairs(found) do
      if not state.names[corpse.id] then
        state.pending_look = {kind = 'corpse', id = corpse.id, at = g_clock.millis()}
        g_game.look(corpse.item)
        break
      end
    end
  end
  if g_clock.millis() - state.last_attempt >= state.config.catchIntervalMs then
    for _, corpse in ipairs(found) do
      local name = state.names[corpse.id]
      if name and selected[name:lower()] and not state.seen[corpse.item] then
        if ballCount() <= 0 then api.stop('no_balls'); return end
        -- Mark before issuing the request: neither errors nor key repeat retry it.
        state.seen[corpse.item] = true
        state.attempts = state.attempts + 1
        state.last_attempt = g_clock.millis()
        state.last_target = {id = corpse.id, name = name, position = corpse.position}
        local ok, error = pcall(g_game.useInventoryItemWith, state.config.ballId, corpse.item)
        if not ok then state.error = tostring(error); api.stop('error'); return end
        break
      end
    end
  end
  state.event = scheduleEvent(scan, 100)
end

function api.configure(config)
  local id = config.ballId or state.config.ballId
  local name = config.ballName or state.balls[id]
  if not state.balls[id] or state.balls[id] ~= name then
    error('Detect balls in an open bag and select a recognized ball')
  end
  local interval = config.catchIntervalMs or state.config.catchIntervalMs
  if type(interval) ~= 'number' or interval ~= math.floor(interval) or interval < 100 or interval > 3000 then
    error('Choose a ball interval between 100 and 3000 milliseconds')
  end
  state.config.ballId, state.config.ballName = id, name
  state.config.catchIntervalMs = interval
  if config.pokemonNames then state.config.pokemonNames = config.pokemonNames end
  return api.status()
end

function api.heartbeat(seconds)
  state.lease = g_clock.millis() + math.min(seconds or 12, 1200) * 1000
  return {enabled = state.enabled}
end

function api.start(config)
  if state.discovery.active then error('Wait for ball detection to finish or cancel it') end
  api.configure(config or {})
  if #state.config.pokemonNames == 0 then return api.stop('no_targets') end
  if not g_game.getLocalPlayer() then return api.stop('offline') end
  api.heartbeat()
  state.reason, state.error = nil, nil
  if not state.enabled then state.enabled = true; scan() end
  return api.status()
end

local function advanceDiscovery()
  local d = state.discovery
  d.checked, d.index = d.checked + 1, d.index + 1
  d.verify_name = nil
  state.pending_look = nil
end

local function stillInOpenBag(target)
  for _, container in pairs(g_game.getContainers()) do
    for _, item in ipairs(container:getItems()) do
      if item == target then return true end
    end
  end
  return false
end

local function discoverStep()
  local d = state.discovery
  d.event = nil
  if not d.active then return end
  local now = g_clock.millis()
  if now > state.lease then finishDiscovery('connection_lost'); return end
  if not g_game.getLocalPlayer() then finishDiscovery('offline'); return end
  if state.pending_look then
    if now - state.pending_look.at >= 2000 then advanceDiscovery() end
  elseif now - state.last_look >= 500 then
    local item = d.queue[d.index]
    if not item then finishDiscovery('complete'); return end
    if not stillInOpenBag(item) then
      advanceDiscovery()
    elseif state.balls[item:getId()] then
      d.found = d.found + 1
      advanceDiscovery()
    else
      state.pending_look = {kind = 'ball', id = item:getId(), count = item:getCount(), at = now,
        verify = d.verify_name}
      state.last_look = now
      local ok = pcall(g_game.look, item)
      if not ok then advanceDiscovery() end
    end
  end
  d.event = scheduleEvent(discoverStep, 200)
end

function api.discover_balls()
  if state.enabled then error('Stop Auto Catch before detecting balls') end
  if state.discovery.active then return api.status() end
  if not g_game.getLocalPlayer() then error('Log in before detecting balls') end
  local queue, seen, has_bag = {}, {}, false
  for _, container in pairs(g_game.getContainers()) do
    has_bag = true
    for _, item in ipairs(container:getItems()) do
      local ok, stackable = pcall(function() return item:isStackable() end)
      if (ok and stackable or item:getCount() > 1) and not seen[item:getId()] and #queue < 256 then
        seen[item:getId()] = true
        queue[#queue + 1] = item
      end
    end
  end
  if not has_bag then error('Open the bag containing your empty balls, then detect again') end
  state.pending_look = nil
  state.discovery = {active = true, checked = 0, total = #queue, found = 0, queue = queue, index = 1}
  api.heartbeat()
  discoverStep()
  return api.status()
end

function api.cancel_ball_discovery()
  if state.discovery.active then finishDiscovery('cancelled') end
  return api.status()
end

-- Used only when loading the catalog saved by the worker for the same build.
function api.restore_ball_catalog(catalog)
  for key, name in pairs(catalog) do
    local id = tonumber(key)
    if id and id == math.floor(id) and id > 0 and id <= 65535 and id ~= 3552
      and type(name) == 'string' and #name <= 80 and name:match(' Ball$') then
      state.balls[id] = name
    end
  end
  return api.status()
end

function api.status()
  local found, pos = corpses()
  local list, catalog, balls = {}, {}, {}
  for id, name in pairs(state.names) do catalog[tostring(id)] = name end
  for id, name in pairs(state.balls) do
    balls[#balls + 1] = {id = id, name = name, count = pos and ballCount(id) or 0}
  end
  table.sort(balls, function(a, b) return a.name < b.name end)
  for _, corpse in ipairs(found) do
    list[#list + 1] = {id = corpse.id, name = corpse.name, position = corpse.position, distance = corpse.distance}
  end
  local d = state.discovery
  return {connected = true, online = pos ~= nil, enabled = state.enabled, attempts = state.attempts,
    ball_count = pos and ballCount() or 0, corpses = list, config = state.config, balls = balls,
    ball_discovery = {active = d.active, checked = d.checked, total = d.total, found = d.found, reason = d.reason},
    last_target = state.last_target, reason = state.reason, error = state.error, last_message = state.last_message,
    catalog = catalog}
end

state.handler = function(mode, text)
  local pending = state.pending_look
  if mode == 20 and type(text) == 'string' and pending and g_clock.millis() - pending.at < 2000 then
    if pending.kind == 'corpse' then
      local name = text:match('^You see defeated (.-) %(')
      if name then state.names[pending.id] = name; state.pending_look = nil end
    elseif pending.kind == 'ball' and text:match('^You see ') then
      local count, name = text:match('^You see (%d+) Empty (.-) Balls?%.')
      if not name then
        name = text:match('^You see an? Empty (.-) Ball%.')
        if name then count = 1 end
      end
      if name then name = name .. ' Ball' end
      if name and #name <= 80 and tonumber(count) == pending.count then
        if not pending.verify then
          -- Confirm with a second Look to avoid learning an unrelated manual Look.
          state.discovery.verify_name = name
          state.pending_look = nil
        else
          if pending.verify == name then
            state.balls[pending.id] = name
            state.discovery.found = state.discovery.found + 1
          end
          advanceDiscovery()
        end
      else
        advanceDiscovery()
      end
    end
  end
  if state.enabled and type(text) == 'string' and (mode == 46 or mode == 47 or text:lower():find('your pokeball', 1, true)) then
    state.last_message = text
  end
end
state.game_end = function() api.stop('offline') end
connect(g_game, {onTextMessage = state.handler, onGameEnd = state.game_end})

function api.shutdown()
  api.stop('disconnected')
  disconnect(g_game, {onTextMessage = state.handler, onGameEnd = state.game_end})
  _G.pokemacroAutoCatch = nil
end

if previous and previous.catalog then
  for id, name in pairs(previous.catalog) do state.names[tonumber(id)] = name end
end
if previous and previous.balls then
  for _, ball in ipairs(previous.balls) do
    api.restore_ball_catalog({[tostring(ball.id)] = ball.name})
  end
end
return json.encode(api.status())
