// banner_carousel.js
document.addEventListener('DOMContentLoaded', () => {
  const slides = document.querySelectorAll(".carousel-slide");
  const dots = document.querySelectorAll(".carousel-dot");
  let currentSlide = 0;
  const totalSlides = slides.length;

  const showSlide = index => {
    slides.forEach((slide, i) => slide.classList.toggle("active", i === index));
    dots.forEach((dot, i) => dot.classList.toggle("bg-[#006A4E]", i === index));
  };

  let slideInterval = setInterval(() => {
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide(currentSlide);
  }, 5000);

  const resetInterval = () => {
    clearInterval(slideInterval);
    slideInterval = setInterval(() => {
      currentSlide = (currentSlide + 1) % totalSlides;
      showSlide(currentSlide);
    }, 5000);
  };

  document.getElementById("next-slide")?.addEventListener("click", () => {
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide(currentSlide);
    resetInterval();
  });
  document.getElementById("prev-slide")?.addEventListener("click", () => {
    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    showSlide(currentSlide);
    resetInterval();
  });
  dots.forEach((dot, i) => dot.addEventListener("click", () => {
    currentSlide = i;
    showSlide(currentSlide);
    resetInterval();
  }));
});
