document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll("[data-tab-panel]");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");

      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      panels.forEach((panel) => {
        const match = panel.getAttribute("data-tab-panel") === tab;
        panel.classList.toggle("hidden", !match);
        panel.classList.toggle("show", match);
      });
    });
  });
});
