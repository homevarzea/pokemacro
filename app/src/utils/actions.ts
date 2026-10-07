import { Combo } from "../types/types";

export const handleAntiLogout = async () => {
  const response = await fetch("/anti-logout", { method: "POST" });
  const data = await response.json();
  return data;
};

export const handleAlert = async () => {
  const response = await fetch("/alert", { method: "POST" });
  const data = await response.json();
  return data;
};

export const handleHealing = async () => {
  const response = await fetch("/healing", { method: "POST" });
  const data = await response.json();
  return data;
};

export const handleAutoCombo = async (combo: Combo) => {
  const response = await fetch("/auto-combo", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ key: combo?.triggerKey?.[0], combo }),
  });
  const data = await response.json();
  return data;
};

export const updateAutoCombo = async (combo: Combo) => {
  const response = await fetch("/update-combo", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      key: combo?.triggerKey?.[0],
      combo: {
        ...combo,
        moveList: combo.moveList.map((move) => ({
          ...move,
          hotkey: move.hotkey || undefined, // Preserve hotkey structure
        })),
      },
    }),
  });
  const data = await response.json();
  return data;
};

export const saveConfig = async (config: any, filename?: string) => {
  const response = await fetch("/save-config", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ config, filename }),
  });
  const data = await response.json();
  return data;
};

export const loadConfig = async (filename?: string) => {
  const response = await fetch("/load-config", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ filename }),
  });
  const data = await response.json();
  return data;
};

export const handleAutoCatch = async (config?: any) => {
  console.log("toggle");
  const response = await fetch("/auto-catch", {
    method: "POST", headers: { 'Content-Type': 'application/json' },
    body: config ? JSON.stringify(config) : undefined,
  });
  const data = await response.json();
  console.log(data);
  return data;
};

export const handleCropImage = async () => {
  const response = await fetch("/crop-image", { method: "POST" });
  const data = await response.json();
  return data;
};

export const getImages = async () => {
  const response = await fetch("/list-images", { method: "GET" });
  const data = await response.json();
  return data;
};

export const deleteImage = async (filename: string) => {
  const response = await fetch(`/delete-image/${filename}`, {
    method: "DELETE",
  });
  const data = await response.json();
  return data;
};

export const renameImage = async (oldFilename: string, newFilename: string) => {
  const response = await fetch("/rename-image", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ oldFilename, newFilename }),
  });
  const data = await response.json();
  return data;
};

export const toggleMouseTracking = async () => {
  const response = await fetch("/toggle-mouse-tracking", { method: "POST" });
  const data = await response.json();
  return data;
};

export const getMouseCoordinates = async () => {
  const response = await fetch("/get-mouse-coords", { method: "GET" });
  const data = await response.json();
  return data;
};

export const clearMouseCoordinates = async () => {
  const response = await fetch("/clear-mouse-coords", { method: "POST" });
  const data = await response.json();
  return data;
};

export const getMouseTrackingCapabilities = async () => {
  const response = await fetch("/mouse-tracking-capabilities", {
    method: "GET",
  });
  const data = await response.json();
  return data;
};

export const handleAutoRevive = async () => {
  const response = await fetch("/auto-revive", { method: "POST" });
  const data = await response.json();
  return data;
};
