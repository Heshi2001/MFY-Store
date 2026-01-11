// scroll_buttons.js
document.addEventListener('DOMContentLoaded', () => {
  const updateArrows = (container, leftBtn, rightBtn) => {
    leftBtn.style.display = container.scrollLeft > 0 ? "block" : "none";
    rightBtn.style.display = container.scrollLeft + container.clientWidth < container.scrollWidth ? "block" : "none";
  };

  const setupScrollSection = (scrollContainer, leftBtn, rightBtn) => {
    if (!scrollContainer || !leftBtn || !rightBtn) return;
    updateArrows(scrollContainer, leftBtn, rightBtn);

    leftBtn.onclick = () => scrollContainer.scrollBy({ left: -300, behavior: "smooth" });
    rightBtn.onclick = () => scrollContainer.scrollBy({ left: 300, behavior: "smooth" });

    scrollContainer.addEventListener("scroll", () => updateArrows(scrollContainer, leftBtn, rightBtn));
    window.addEventListener("resize", () => updateArrows(scrollContainer, leftBtn, rightBtn));
  };

  const featuredScroll = document.getElementById("scroll-featured");
  const featuredLeft = document.getElementById("scroll-left-featured");
  const featuredRight = document.getElementById("scroll-right-featured");
  setupScrollSection(featuredScroll, featuredLeft, featuredRight);

  document.querySelectorAll("section").forEach(section => {
    const scrollContainer = section.querySelector(".product-scroll");
    const leftBtn = section.querySelector(".scroll-left");
    const rightBtn = section.querySelector(".scroll-right");
    setupScrollSection(scrollContainer, leftBtn, rightBtn);
  });
});
