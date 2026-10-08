import React, {
  createContext,
  Dispatch,
  PropsWithChildren,
  SetStateAction,
  useEffect,
  useState,
} from "react";
import useConfig from "../hooks/useConfig";

export interface SelectedImage {
  filename: string;
  label: string;
}

export interface AutoCatchConfig {
  selectedImages: SelectedImage[];
  hotkey: string;
  mode: 'game' | 'image';
  ballId: number;
  ballName: string;
  catchIntervalMs: number;
  pokemonNames: string[];
}

export const defaultAutoCatchConfig: AutoCatchConfig = {
  selectedImages: [],
  hotkey: "",
  mode: 'game',
  ballId: 3552,
  ballName: 'Ultra Ball',
  catchIntervalMs: 500,
  pokemonNames: ['Oddish', 'Gloom'],
};

type AutoCatchContextType = {
  autoCatchConfig: AutoCatchConfig;
  setAutoCatchConfig: Dispatch<SetStateAction<AutoCatchConfig>>;
};

const AutoCatchContext = createContext<AutoCatchContextType>(
  {} as AutoCatchContextType
);

const AutoCatchProvider = ({ children }: PropsWithChildren) => {
  const { loadConfig, saveConfig } = useConfig();
  const [autoCatchConfig, setAutoCatchConfig] = useState<AutoCatchConfig>(
    defaultAutoCatchConfig
  );
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    (async () => {
      const config = await loadConfig("autocatch.json");
      console.log("Loaded config:", config);
      if (config && Object.keys(config).length > 0) {
        setAutoCatchConfig({
          selectedImages: config.selectedImages || [],
          hotkey: config.hotkey || defaultAutoCatchConfig.hotkey,
          mode: config.mode || 'game',
          ballId: config.ballId || 3552,
          ballName: config.ballName || (!config.ballId || config.ballId === 3552 ? 'Ultra Ball' : ''),
          catchIntervalMs: config.catchIntervalMs || 500,
          pokemonNames: config.pokemonNames || ['Oddish', 'Gloom'],
        });
      }
      setInitialized(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (initialized) {
      console.log("Saving config:", autoCatchConfig);
      saveConfig(autoCatchConfig, "autocatch.json")
        .then((response) => {
          console.log("AutoCatch config saved:", response);
        })
        .catch((error) => {
          console.error("Error saving AutoCatch config:", error);
        });
    }
  }, [autoCatchConfig, initialized, saveConfig]);

  return (
    <AutoCatchContext.Provider value={{ autoCatchConfig, setAutoCatchConfig }}>
      {children}
    </AutoCatchContext.Provider>
  );
};

export { AutoCatchProvider, AutoCatchContext };
export type { AutoCatchContextType };
