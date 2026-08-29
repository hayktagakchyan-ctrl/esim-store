(function () {
  function getPreferredTheme() {
    const saved = localStorage.getItem("site_theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const toggle = document.getElementById("theme-toggle");
    if (toggle) toggle.setAttribute("aria-checked", theme === "dark" ? "true" : "false");
  }

  const theme = getPreferredTheme();
  applyTheme(theme);

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;
    toggle.setAttribute("aria-checked", theme === "dark" ? "true" : "false");
    toggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("site_theme", next);
      applyTheme(next);
    });
  });
})();
