(function () {
  var STORAGE_KEY = "uma-theme";
  var root = document.documentElement;
  var themeButtons = [];

  function getStoredMode() {
    var mode = localStorage.getItem(STORAGE_KEY);
    if (mode === "light" || mode === "dark" || mode === "system") {
      return mode;
    }
    return "system";
  }

  function getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function resolveTheme(mode) {
    return mode === "system" ? getSystemTheme() : mode;
  }

  function iconForMode(mode) {
    if (mode === "light") return "☀";
    if (mode === "dark") return "☾";
    return "◐";
  }

  function labelForMode(mode) {
    if (mode === "light") return "主題：淺色";
    if (mode === "dark") return "主題：深色";
    return "主題：跟隨系統";
  }

  function applyMode(mode) {
    var appliedTheme = resolveTheme(mode);
    root.setAttribute("data-theme", appliedTheme);
    root.setAttribute("data-theme-mode", mode);
    localStorage.setItem(STORAGE_KEY, mode);

    themeButtons.forEach(function (btn) {
      btn.textContent = iconForMode(mode);
      btn.setAttribute("title", labelForMode(mode));
      btn.setAttribute("aria-label", labelForMode(mode));
      btn.setAttribute("data-theme-mode", mode);
    });
  }

  function cycleMode() {
    var current = root.getAttribute("data-theme-mode") || getStoredMode();
    var next = "system";
    if (current === "system") next = "light";
    else if (current === "light") next = "dark";
    applyMode(next);
  }

  function init() {
    themeButtons = Array.prototype.slice.call(
      document.querySelectorAll("#themeToggleBtn, #themeBtn")
    );
    if (!themeButtons.length) {
      return;
    }

    var mode = getStoredMode();
    applyMode(mode);
    themeButtons.forEach(function (btn) {
      btn.addEventListener("click", cycleMode);
    });

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      var current = root.getAttribute("data-theme-mode") || getStoredMode();
      if (current === "system") {
        applyMode("system");
      }
    });
  }

  window.UmaTheme = {
    applyMode: applyMode,
    getStoredMode: getStoredMode,
  };

  document.addEventListener("DOMContentLoaded", init);
})();
