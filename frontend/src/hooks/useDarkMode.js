import { useEffect, useState } from "react";

export function useDarkMode() {
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") return true;
    if (saved === "light") return false;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      if (localStorage.getItem("theme")) localStorage.setItem("theme", "dark");
    } else {
      root.classList.remove("dark");
      if (localStorage.getItem("theme")) localStorage.setItem("theme", "light");
    }
  }, [isDark]);

  const setExplicitDark = (value) => {
    const next = typeof value === "function" ? value(isDark) : value;
    localStorage.setItem("theme", next ? "dark" : "light");
    setIsDark(next);
  };

  return [isDark, setExplicitDark];
}
