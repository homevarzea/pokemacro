import React, { useState, useContext, useEffect } from "react";
import Button from "../components/Button/Button";
import { handleCropImage } from "../utils/actions";
import ImagesGrid from "../components/ImagesGrid";
import { AutoCatchContext } from "../contexts/AutoCatchContext";
import KeybindingPicker from "../components/KeybindingPicker";
import PageWrapper from "../components/PageWrapper";
import { CameraIcon, PhotoIcon } from "@heroicons/react/24/outline";
import * as GlobalContext from '../contexts/GlobalContext';
import { handleAutoCatch } from '../utils/actions';

type BallChoice = { id: number; name: string; count?: number };

const AutoCatch = () => {
  const [loading, setLoading] = useState(false);
  const [refreshGrid, setRefreshGrid] = useState(0);
  const { autoCatchConfig, setAutoCatchConfig } = useContext(AutoCatchContext);
  const { autoCatch, setAutoCatch } = useContext(GlobalContext.Context);
  const [bridge, setBridge] = useState<any>({ connected: false });
  const [error, setError] = useState('');
  const [pokemonName, setPokemonName] = useState('');

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const data = await (await fetch('/game-bridge/status')).json();
        if (active) {
          setBridge(data);
          if (autoCatchConfig.mode === 'game') setAutoCatch(Boolean(data.enabled));
        }
      } catch { /* Show the latest connection state while the app restarts. */ }
    };
    refresh();
    const timer = window.setInterval(refresh, 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [autoCatchConfig.mode, setAutoCatch]);

  const connectGame = async () => {
    setLoading(true); setError('');
    try {
      const data = await (await fetch('/game-bridge/connect', { method: 'POST' })).json();
      setBridge(data);
      if (data.error) setError(data.error);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const toggleGameCatch = async () => {
    setLoading(true); setError('');
    try {
      const result = await handleAutoCatch(autoCatchConfig);
      setAutoCatch(Boolean(result.auto_catch_enabled));
      if (result.game) setBridge(result.game);
      if (result.error) setError(result.error);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const detectBalls = async (cancel = false) => {
    setLoading(true); setError('');
    try {
      const path = cancel ? '/game-bridge/balls/cancel' : '/game-bridge/balls/detect';
      const data = await (await fetch(path, { method: 'POST' })).json();
      if (data.error) setError(data.error);
      else setBridge(data);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const ballMap = new Map<number, BallChoice>([[3552, { id: 3552, name: 'Ultra Ball' }]]);
  if (autoCatchConfig.ballName) ballMap.set(autoCatchConfig.ballId, { id: autoCatchConfig.ballId, name: autoCatchConfig.ballName });
  for (const ball of (Array.isArray(bridge.balls) ? bridge.balls : []) as BallChoice[]) ballMap.set(ball.id, ball);
  const ballChoices = Array.from(ballMap.values()).sort((a, b) => a.name.localeCompare(b.name));
  const selectedBall = ballMap.get(autoCatchConfig.ballId);
  const discovery = bridge.ball_discovery;
  const detecting = Boolean(discovery?.active);

  const choices = Array.from(new Set<string>([
    'Oddish', 'Gloom', ...autoCatchConfig.pokemonNames,
    ...Object.values(bridge.catalog || {}) as string[],
  ])).sort();

  const addPokemon = () => {
    const name = pokemonName.trim();
    if (!name) return;
    setAutoCatchConfig(prev => ({ ...prev, pokemonNames: Array.from(new Set([...prev.pokemonNames, name])) }));
    setPokemonName('');
  };

  const startNewCrop = async () => {
    setLoading(true);
    try {
      const result = await handleCropImage();
      if (result.image) {
        setRefreshGrid((prev) => prev + 1);
      }
    } catch (error) {
      console.error("Failed to crop image:", error);
    }
    setLoading(false);
  };

  return (
    <PageWrapper
      title="Auto Catch"
      subtitle="Choose Pokémon by name and catch their corpses using game data"
    >
      <div className="flex gap-3 mb-6">
        {(['game', 'image'] as const).map(mode => (
          <Button key={mode} disabled={autoCatch || detecting} variant={autoCatchConfig.mode === mode ? 'primary' : 'default'}
            onClick={() => setAutoCatchConfig(prev => ({ ...prev, mode }))}>
            {mode === 'game' ? 'Game data' : 'Image recognition'}
          </Button>
        ))}
      </div>
      {autoCatchConfig.mode === 'game' ? (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 flex flex-wrap items-center gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-100">Poke Alliance</h3>
              <p className="text-sm text-gray-400 mt-1">
                {bridge.connected ? (bridge.online ? 'Character connected' : 'Log in to your character') : 'Connect to the open game; Windows may request administrator access.'}
              </p>
              {bridge.connected && <p className="text-sm text-gray-300 mt-2">{autoCatchConfig.ballName}: {selectedBall?.count ?? '—'} · Attempts: {bridge.attempts ?? 0}</p>}
            </div>
            {!bridge.connected && <Button onClick={connectGame} disabled={loading} variant="default">{loading ? 'Connecting...' : 'Connect to game'}</Button>}
            <Button onClick={toggleGameCatch} disabled={loading || detecting || (!autoCatch && (autoCatchConfig.pokemonNames.length === 0 || !autoCatchConfig.ballName))} variant="primary">
              {autoCatch ? 'Stop Auto Catch' : 'Start Auto Catch'}
            </Button>
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
            <h3 className="text-base font-semibold text-gray-100">Ball to use</h3>
            <p className="text-sm text-gray-400 mt-1">Open the bag containing your empty balls and click Detect balls. Choose a name below; your selection is saved automatically.</p>
            <div className="flex flex-wrap items-center gap-3 mt-4">
              <label htmlFor="catch-ball" className="text-sm text-gray-300">Ball</label>
              <select id="catch-ball" value={autoCatchConfig.ballId} disabled={autoCatch || loading || detecting}
                onChange={e => {
                  const ball = ballMap.get(Number(e.target.value));
                  if (ball) setAutoCatchConfig(prev => ({ ...prev, ballId: ball.id, ballName: ball.name }));
                }}
                className="bg-gray-900 border border-gray-600 rounded px-3 py-2 text-gray-100 min-w-[200px]">
                {!autoCatchConfig.ballName && <option value={autoCatchConfig.ballId}>Detect and select a ball</option>}
                {ballChoices.map(ball => <option key={ball.id} value={ball.id}>{ball.name}{ball.count !== undefined ? ` (${ball.count})` : ''}</option>)}
              </select>
              {detecting
                ? <Button onClick={() => detectBalls(true)} disabled={loading} variant="default">Cancel detection</Button>
                : <Button onClick={() => detectBalls()} disabled={autoCatch || loading} variant="default">{loading ? 'Please wait...' : 'Detect balls'}</Button>}
            </div>
            {detecting && <p role="status" className="text-sm text-gray-300 mt-3">Checking bag items: {discovery.checked}/{discovery.total}. Keep the bag open until detection finishes.</p>}
            {!detecting && discovery?.reason === 'complete' && <p role="status" className="text-sm text-gray-300 mt-3">Detection complete: {discovery.found} ball types recognized. Open other bags and detect again to add more.</p>}
            {autoCatch && <p className="text-sm text-gray-400 mt-3">Stop Auto Catch to change the ball or detect more balls.</p>}
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
            <h3 className="text-base font-semibold text-gray-100">Pokémon to catch</h3>
            <p className="text-sm text-gray-400 mt-1">Select names or add a name. New corpses are identified from the game's own description.</p>
            <div className="flex flex-wrap gap-4 mt-4">
              {choices.map(name => <label key={name} className="flex items-center gap-2 text-gray-200">
                <input type="checkbox" disabled={autoCatch} checked={autoCatchConfig.pokemonNames.includes(name)}
                  onChange={e => setAutoCatchConfig(prev => ({ ...prev, pokemonNames: e.target.checked ? [...prev.pokemonNames, name] : prev.pokemonNames.filter(n => n !== name) }))} />
                {name}
              </label>)}
            </div>
            <div className="flex gap-3 mt-5">
              <input aria-label="Pokémon name" placeholder="Pokémon name" value={pokemonName} disabled={autoCatch}
                onChange={e => setPokemonName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') addPokemon(); }}
                className="bg-gray-900 border border-gray-600 rounded px-3 py-2 text-gray-100" />
              <Button onClick={addPokemon} disabled={autoCatch || !pokemonName.trim()} variant="default">Add Pokémon</Button>
            </div>
            <p className="text-sm text-gray-400 mt-5">Uses {autoCatchConfig.ballName || 'the selected ball'}, with one attempt per visible corpse. It stops when that ball runs out.</p>
            {bridge.last_target && <p className="text-sm text-gray-300 mt-3">Last target: {bridge.last_target.name}</p>}
            {bridge.last_message && <p className="text-sm text-gray-300 mt-1">{bridge.last_message}</p>}
            {(error || bridge.error) && <p role="alert" className="text-sm text-red-400 mt-3">{error || bridge.error}</p>}
            {bridge.reason && bridge.reason !== 'disabled' && !bridge.enabled && <p className="text-sm text-gray-400 mt-3">Stopped: {bridge.reason.replace(/_/g, ' ')}</p>}
          </div>
        </div>
      ) : (
      <div className="flex gap-6">
        {/* Images Grid */}
        <div className="flex-[2] bg-gray-800 rounded-lg border border-gray-700">
          <div className="flex items-center gap-3 p-6 border-b border-gray-700">
            <PhotoIcon className="w-5 h-5 text-green-400" />
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-100">
                Recognition Images
              </h3>
              <p className="text-sm text-gray-400">
                Select which Pokemon images to automatically catch
              </p>
            </div>
            <Button
              onClick={startNewCrop}
              variant="primary"
              disabled={loading}
              className="flex items-center gap-2"
            >
              <CameraIcon className="w-4 h-4" />
              {loading ? "Cropping..." : "New Crop"}
            </Button>
          </div>
          <div className="p-6">
            <ImagesGrid
              refresh={refreshGrid}
              initialSelected={autoCatchConfig.selectedImages}
            />
          </div>
        </div>
        {/* Hotkey Configuration */}
        <div className="flex-[1] bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center gap-3 mb-4">
            <h3 className="text-base font-semibold text-gray-100">
              Auto Catch Hotkey
            </h3>
          </div>
          <div className="max-w-xs">
            <KeybindingPicker
              key={autoCatchConfig.hotkey}
              name="autocatch-hotkey"
              currentKey={autoCatchConfig.hotkey || ""}
              onKeySelected={(selectedKey) => {
                setAutoCatchConfig((prev) => {
                  const current = prev;
                  return {
                    ...current,
                    hotkey: selectedKey.keyName || current.hotkey,
                  };
                });
              }}
            />
          </div>
          <p className="text-sm text-gray-400 mt-2">
            Press this key to trigger auto catch when Pokemon appear
          </p>
        </div>
      </div>
      )}
    </PageWrapper>
  );
};

export default AutoCatch;
