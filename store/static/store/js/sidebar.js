document.addEventListener("click", function (e) {

  const toggleBtn = e.target.closest(".toggle-sub");

  // ✅ Only toggle logic
  if (toggleBtn) {
    e.preventDefault();
    e.stopPropagation();

    const parent = toggleBtn.closest("li");
    const subList = parent.querySelector(":scope > .sub-list");
    const arrow = toggleBtn.querySelector(".arrow");

    if (!subList) return;

    const isOpen = subList.classList.contains("open");

    // CLOSE siblings
    const siblings = parent.parentElement.children;
    Array.from(siblings).forEach(li => {
      const sub = li.querySelector(":scope > .sub-list");
      const arr = li.querySelector(".arrow");

      if (sub && sub !== subList) {
        sub.style.maxHeight = null;
        sub.classList.remove("open");
        if (arr) arr.classList.remove("rotate-90");
      }
    });

    // TOGGLE current
    if (isOpen) {
      subList.style.maxHeight = null;
      subList.classList.remove("open");
      arrow.classList.remove("rotate-90");
    } else {
      subList.style.maxHeight = subList.scrollHeight + "px";
      subList.classList.add("open");
      arrow.classList.add("rotate-90");
    }

    return;
  }

});