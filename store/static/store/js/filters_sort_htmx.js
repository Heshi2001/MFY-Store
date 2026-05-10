window._mfy = window._mfy || {};

// =========================
// SORT DROPDOWN
// =========================
function initSortDropdown() {
  const sortBtn   = document.getElementById('sort-toggle');
  const dropdown  = document.getElementById('sort-dropdown');
  const arrow     = document.getElementById('sort-arrow');
  const sortLabel = document.getElementById('sort-label');

  if (!sortBtn || !dropdown) return;
  if (sortBtn.dataset.bound === "true") return;
  sortBtn.dataset.bound = "true";

  // Toggle open/close
  sortBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = !dropdown.classList.contains('hidden');
    dropdown.classList.toggle('hidden', isOpen);
    arrow?.classList.toggle('rotate-180', !isOpen);
  });

  // Update label + close on option click
  dropdown.addEventListener('click', (e) => {
    const option = e.target.closest('.sort-option');
    if (!option) return;
    if (sortLabel) sortLabel.textContent = option.dataset.label || 'Sort';
    dropdown.classList.add('hidden');
    arrow?.classList.remove('rotate-180');
  });

  // Close on outside click — bind once globally
  if (!window._mfy.sortOutsideBound) {
    window._mfy.sortOutsideBound = true;
    document.addEventListener('click', () => {
      document.getElementById('sort-dropdown')?.classList.add('hidden');
      document.getElementById('sort-arrow')?.classList.remove('rotate-180');
    });
  }
}

// =========================
// FILTER APPLY/CLEAR
// =========================
function initFilters() {
  const applyBtn = document.getElementById('apply-filter');
  const clearBtn = document.getElementById('clear-filter');
  const badge    = document.getElementById('filter-badge');

  if (applyBtn && !applyBtn.dataset.bound) {
    applyBtn.dataset.bound = "true";

    applyBtn.addEventListener('click', () => {
      const min = document.getElementById('min-price')?.value.trim();
      const max = document.getElementById('max-price')?.value.trim();

      // ✅ Sync hidden filter form for hx-include
      document.getElementById('ff-min').value = min || '';
      document.getElementById('ff-max').value = max || '';

      // ✅ Brand checkboxes → hidden inputs
      const brandsContainer = document.getElementById('ff-brands');
      brandsContainer.innerHTML = '';
      document.querySelectorAll('.brand-checkbox:checked').forEach(cb => {
        const input = document.createElement('input');
        input.type  = 'hidden';
        input.name  = 'brand';
        input.value = cb.value;
        brandsContainer.appendChild(input);
      });

      // ✅ Build params
      const params = new URLSearchParams(window.location.search);
      if (min) params.set('min_price', min); else params.delete('min_price');
      if (max) params.set('max_price', max); else params.delete('max_price');

      params.delete('brand');
      document.querySelectorAll('.brand-checkbox:checked').forEach(cb => {
        params.append('brand', cb.value);
      });

      // ✅ Badge count
      let count = 0;
      if (min) count++;
      if (max) count++;
      count += document.querySelectorAll('.brand-checkbox:checked').length;

      if (badge) {
        badge.textContent = count;
        badge.classList.toggle('hidden', count === 0);
      }

      // ✅ Fire HTMX
      const url = window.location.pathname + '?' + params.toString();
      htmx.ajax('GET', url, {
        target: '#product-grid',
        swap: 'innerHTML',
        pushUrl: true,
      });
    });
  }

  if (clearBtn && !clearBtn.dataset.bound) {
    clearBtn.dataset.bound = "true";

    clearBtn.addEventListener('click', () => {
      document.getElementById('min-price').value = '';
      document.getElementById('max-price').value = '';
      document.querySelectorAll('.brand-checkbox').forEach(cb => cb.checked = false);
      document.getElementById('ff-brands').innerHTML = '';
      document.getElementById('ff-min').value = '';
      document.getElementById('ff-max').value = '';
      if (badge) badge.classList.add('hidden');
    });
  }
}

// =========================
// COUNT UPDATE (OOB)
// =========================
function updateCount(countText) {
  const el = document.getElementById('product-count');
  if (el) el.textContent = countText;
}

// =========================
// HTMX LOADING UX
// =========================
document.body.addEventListener('htmx:beforeRequest', (e) => {
  if (e.detail.target?.id !== 'product-grid') return;
  document.getElementById('product-grid')?.classList.add('opacity-0');
  document.getElementById('shimmer-loader')?.classList.remove('hidden');
});

document.body.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target?.id !== 'product-grid') return;
  document.getElementById('shimmer-loader')?.classList.add('hidden');
  document.getElementById('product-grid')?.classList.remove('opacity-0');

  // ✅ Re-init after HTMX swap
  initSortDropdown();
  initFilters();
});

// ✅ Handle OOB count update from _product_wrapper.html
document.body.addEventListener('htmx:oobAfterSwap', (e) => {
  // count div auto-swapped by HTMX OOB
});

// =========================
// INIT ON LOAD
// =========================
document.addEventListener('DOMContentLoaded', () => {
  initSortDropdown();
  initFilters();
});