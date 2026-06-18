export interface ColorThemeColors {
  background: [string, string, ...string[]];
  cardBg: string;
  cardBorder: string;
  text: string;
  subtext: string;
  accent: string;
  buttonText: string;
  inputBg: string;
  inputBorder: string;
  selectorBg: string;
  selectorText: string;
  activeSelectorBg: string;
  activeSelectorText: string;
}

export interface ThemeConfig {
  name: string;
  light: ColorThemeColors;
  dark: ColorThemeColors;
}

export const MOBILE_THEMES: Record<string, ThemeConfig> = {
  ocean: {
    name: "🌊 Ocean",
    light: {
      background: ["#60a5fa", "#22d3ee", "#2dd4bf"],
      cardBg: "rgba(255, 255, 255, 0.75)",
      cardBorder: "rgba(255, 255, 255, 0.4)",
      text: "#1e3a8a",
      subtext: "#475569",
      accent: "#2563eb",
      buttonText: "#ffffff",
      inputBg: "#ffffff",
      inputBorder: "#93c5fd",
      selectorBg: "#bfdbfe",
      selectorText: "#1e3a8a",
      activeSelectorBg: "#2563eb",
      activeSelectorText: "#ffffff",
    },
    dark: {
      background: ["#1e3a8a", "#0c4a6e", "#115e59"],
      cardBg: "rgba(15, 23, 42, 0.8)",
      cardBorder: "rgba(255, 255, 255, 0.1)",
      text: "#f0f9ff",
      subtext: "#94a3b8",
      accent: "#38bdf8",
      buttonText: "#ffffff",
      inputBg: "#1e293b",
      inputBorder: "#334155",
      selectorBg: "#334155",
      selectorText: "#94a3b8",
      activeSelectorBg: "#38bdf8",
      activeSelectorText: "#0f172a",
    },
  },
  sunset: {
    name: "🌅 Sunset",
    light: {
      background: ["#fb923c", "#f43f5e", "#db2777"],
      cardBg: "rgba(255, 255, 255, 0.75)",
      cardBorder: "rgba(255, 255, 255, 0.4)",
      text: "#7c2d12",
      subtext: "#4f4f4f",
      accent: "#ea580c",
      buttonText: "#ffffff",
      inputBg: "#ffffff",
      inputBorder: "#fed7aa",
      selectorBg: "#ffedd5",
      selectorText: "#7c2d12",
      activeSelectorBg: "#ea580c",
      activeSelectorText: "#ffffff",
    },
    dark: {
      background: ["#7c2d12", "#4c0519", "#881337"],
      cardBg: "rgba(24, 24, 27, 0.8)",
      cardBorder: "rgba(255, 255, 255, 0.1)",
      text: "#ffe4e6",
      subtext: "#fda4af",
      accent: "#fb7185",
      buttonText: "#ffffff",
      inputBg: "#27272a",
      inputBorder: "#3f3f46",
      selectorBg: "#3f3f46",
      selectorText: "#a1a1aa",
      activeSelectorBg: "#fb7185",
      activeSelectorText: "#000000",
    },
  },
  forest: {
    name: "🌿 Forest",
    light: {
      background: ["#4ade80", "#10b981", "#0d9488"],
      cardBg: "rgba(255, 255, 255, 0.75)",
      cardBorder: "rgba(255, 255, 255, 0.4)",
      text: "#064e3b",
      subtext: "#374151",
      accent: "#047857",
      buttonText: "#ffffff",
      inputBg: "#ffffff",
      inputBorder: "#a7f3d0",
      selectorBg: "#d1fae5",
      selectorText: "#064e3b",
      activeSelectorBg: "#047857",
      activeSelectorText: "#ffffff",
    },
    dark: {
      background: ["#064e3b", "#065f46", "#115e59"],
      cardBg: "rgba(15, 23, 42, 0.8)",
      cardBorder: "rgba(255, 255, 255, 0.1)",
      text: "#ecfdf5",
      subtext: "#a7f3d0",
      accent: "#34d399",
      buttonText: "#064e3b",
      inputBg: "#1e293b",
      inputBorder: "#334155",
      selectorBg: "#334155",
      selectorText: "#94a3b8",
      activeSelectorBg: "#34d399",
      activeSelectorText: "#064e3b",
    },
  },
  purple: {
    name: "💜 Purple",
    light: {
      background: ["#c084fc", "#8b5cf6", "#d946ef"],
      cardBg: "rgba(255, 255, 255, 0.75)",
      cardBorder: "rgba(255, 255, 255, 0.4)",
      text: "#4c1d95",
      subtext: "#374151",
      accent: "#7c3aed",
      buttonText: "#ffffff",
      inputBg: "#ffffff",
      inputBorder: "#ddd6fe",
      selectorBg: "#ede9fe",
      selectorText: "#4c1d95",
      activeSelectorBg: "#7c3aed",
      activeSelectorText: "#ffffff",
    },
    dark: {
      background: ["#4c1d95", "#2e1065", "#5b21b6"],
      cardBg: "rgba(24, 24, 27, 0.8)",
      cardBorder: "rgba(255, 255, 255, 0.1)",
      text: "#f5f3ff",
      subtext: "#c084fc",
      accent: "#a78bfa",
      buttonText: "#ffffff",
      inputBg: "#27272a",
      inputBorder: "#3f3f46",
      selectorBg: "#3f3f46",
      selectorText: "#a1a1aa",
      activeSelectorBg: "#a78bfa",
      activeSelectorText: "#1e1b4b",
    },
  },
  mono: {
    name: "🖤 Mono",
    light: {
      background: ["#cbd5e1", "#94a3b8", "#64748b"],
      cardBg: "rgba(255, 255, 255, 0.75)",
      cardBorder: "rgba(255, 255, 255, 0.4)",
      text: "#1e293b",
      subtext: "#475569",
      accent: "#334155",
      buttonText: "#ffffff",
      inputBg: "#ffffff",
      inputBorder: "#cbd5e1",
      selectorBg: "#e2e8f0",
      selectorText: "#1e293b",
      activeSelectorBg: "#334155",
      activeSelectorText: "#ffffff",
    },
    dark: {
      background: ["#1e293b", "#0f172a", "#030712"],
      cardBg: "rgba(24, 24, 27, 0.8)",
      cardBorder: "rgba(255, 255, 255, 0.1)",
      text: "#f8fafc",
      subtext: "#94a3b8",
      accent: "#94a3b8",
      buttonText: "#0f172a",
      inputBg: "#1e293b",
      inputBorder: "#334155",
      selectorBg: "#334155",
      selectorText: "#94a3b8",
      activeSelectorBg: "#f8fafc",
      activeSelectorText: "#0f172a",
    },
  },
};
