(() => {
  const button = document.querySelector("#headerShortcutsBtn");
  if (!button) return;
  button.addEventListener("click", event => {
    event.preventDefault();
    if (typeof window.toggleDesktopDashboardShortcuts === "function") window.toggleDesktopDashboardShortcuts();
  });
})();
