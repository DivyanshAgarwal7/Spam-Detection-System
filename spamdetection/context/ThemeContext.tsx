import React, { createContext, useContext, useState, useEffect } from "react";
import { useColorScheme } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { MOBILE_THEMES, ColorThemeColors, ThemeConfig } from "../constants/themes";

interface ThemeContextType {
  themeMode: "light" | "dark" | "system";
  setThemeMode: (mode: "light" | "dark" | "system") => void;
  colorTheme: string;
  setColorTheme: (theme: string) => void;
  isDark: boolean;
  activeColors: ColorThemeColors;
}

const ThemeContext = createContext<ThemeContextType | null>(null);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const systemScheme = useColorScheme();
  const [themeMode, setThemeModeState] = useState<"light" | "dark" | "system">("system");
  const [colorTheme, setColorThemeState] = useState<string>("ocean");
  const [isDark, setIsDark] = useState<boolean>(false);

  // Load saved preferences
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const savedMode = await AsyncStorage.getItem("themeMode");
        const savedColor = await AsyncStorage.getItem("colorTheme");
        if (savedMode) {
          setThemeModeState(savedMode as "light" | "dark" | "system");
        }
        if (savedColor) {
          setColorThemeState(savedColor);
        }
      } catch (e) {
        console.warn("Failed to load theme settings:", e);
      }
    };
    loadSettings();
  }, []);

  // Update resolved dark mode when themeMode or systemScheme changes
  useEffect(() => {
    if (themeMode === "system") {
      setIsDark(systemScheme === "dark");
    } else {
      setIsDark(themeMode === "dark");
    }
  }, [themeMode, systemScheme]);

  const setThemeMode = async (mode: "light" | "dark" | "system") => {
    setThemeModeState(mode);
    try {
      await AsyncStorage.setItem("themeMode", mode);
    } catch (e) {
      console.warn("Failed to save themeMode:", e);
    }
  };

  const setColorTheme = async (theme: string) => {
    setColorThemeState(theme);
    try {
      await AsyncStorage.setItem("colorTheme", theme);
    } catch (e) {
      console.warn("Failed to save colorTheme:", e);
    }
  };

  const resolvedThemeConfig: ThemeConfig = MOBILE_THEMES[colorTheme] || MOBILE_THEMES.ocean;
  const activeColors: ColorThemeColors = isDark ? resolvedThemeConfig.dark : resolvedThemeConfig.light;

  return (
    <ThemeContext.Provider
      value={{
        themeMode,
        setThemeMode,
        colorTheme,
        setColorTheme,
        isDark,
        activeColors,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};
