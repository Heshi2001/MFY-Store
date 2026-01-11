document.addEventListener('DOMContentLoaded', () => {
const faqButtons = document.querySelectorAll('[data-accordion-target]');

  faqButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.querySelector(btn.dataset.accordionTarget);
      const icon = btn.querySelector('i');

      // Close other FAQs (optional: comment this block if you want multiple open)
      document.querySelectorAll('.faq-answer.open').forEach(openFaq => {
        if (openFaq !== target) {
          openFaq.style.maxHeight = null;
          openFaq.classList.remove('open');
        }
      });
      document.querySelectorAll('[data-accordion-target] i').forEach(i => {
        if (i !== icon) i.classList.remove('rotate-180', 'text-green-400');
        if (i !== icon) i.classList.add('text-gray-400');
      });

      // Toggle current FAQ
      if (target.classList.contains('open')) {
        target.style.maxHeight = null;
        target.classList.remove('open');
        icon.classList.remove('rotate-180', 'text-green-400');
        icon.classList.add('text-gray-400');
      } else {
        target.classList.add('open');
        target.style.maxHeight = target.scrollHeight + 'px';
        icon.classList.add('rotate-180', 'text-green-400');
        icon.classList.remove('text-gray-400');

        // ✅ Adjusted smooth scroll (fixes jump issue)
        setTimeout(() => {
          const rect = btn.getBoundingClientRect();
          const offset = window.scrollY + rect.top - 100; // slight offset below navbar
          window.scrollTo({ top: offset, behavior: 'smooth' });
        }, 300);
      }
    });
  });
 });