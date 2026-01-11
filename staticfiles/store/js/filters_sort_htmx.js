// ensure buttons that should not submit are explicitly non-submit
const sortBtn = document.getElementById('sort-toggle');
const sortDropdown = document.getElementById('sort-dropdown');
const sortArrow = document.getElementById('sort-arrow');

// make sure these exist before using them
const filterBtn = document.getElementById('filter-btn');
const filterModal = document.getElementById('filter-modal');
const filterPanel = document.getElementById('filter-panel');
const closeFilter = document.getElementById('close-filter');
const applyFilter = document.getElementById('apply-filter');
const clearFilter = document.getElementById('clear-filter');
const badge = document.getElementById('filter-badge');

// Safety: ensure button types
if (sortBtn && !sortBtn.hasAttribute('type')) sortBtn.setAttribute('type', 'button');
if (filterBtn && !filterBtn.hasAttribute('type')) filterBtn.setAttribute('type', 'button');
if (applyFilter && !applyFilter.hasAttribute('type')) applyFilter.setAttribute('type', 'button');
if (clearFilter && !clearFilter.hasAttribute('type')) clearFilter.setAttribute('type', 'button');

// --- SORT ---
if (sortBtn && sortDropdown && sortArrow) {
  sortBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const isOpen = !sortDropdown.classList.contains('hidden');
    sortDropdown.classList.toggle('hidden');
    sortArrow.classList.toggle('rotate-180', !isOpen);
  });

  document.addEventListener('click', (e) => {
    if (!sortBtn.contains(e.target) && !sortDropdown.contains(e.target)) {
      sortDropdown.classList.add('hidden');
      sortArrow.classList.remove('rotate-180');
    }
  });
}

// --- FILTER MODAL ---
function openFilter(e) {
  if (e) { e.preventDefault(); e.stopPropagation(); }
  if (!filterModal || !filterPanel) return;
  filterModal.classList.remove('hidden');
  setTimeout(() => {
    filterPanel.classList.remove('translate-y-full', 'sm:translate-x-full');
  }, 10);
}
function closeFilterModal(e) {
  if (e) { e.preventDefault(); e.stopPropagation(); }
  if (!filterModal || !filterPanel) return;
  filterPanel.classList.add('translate-y-full', 'sm:translate-x-full');
  setTimeout(() => filterModal.classList.add('hidden'), 300);
}

if (filterBtn) filterBtn.addEventListener('click', openFilter);
if (closeFilter) closeFilter.addEventListener('click', closeFilterModal);
if (filterModal) {
  filterModal.addEventListener('click', e => {
    if (e.target === filterModal) closeFilterModal(e);
  });
}

// --- APPLY & CLEAR ---
if (applyFilter) {
  applyFilter.addEventListener('click', () => {
    const cats = Array.from(document.querySelectorAll('input[name="category"]:checked')).map(el => el.value);
    const min = document.getElementById('min-price').value;
    const max = document.getElementById('max-price').value;

    badge.textContent = cats.length + (min || max ? 1 : 0);
    badge.classList.toggle('hidden', badge.textContent === '0');

    const params = new URLSearchParams();
    if (cats.length) params.append('category', cats.join(','));
    if (min) params.append('min_price', min);
    if (max) params.append('max_price', max);

    htmx.ajax('GET', `/fetch-products/?${params.toString()}`, {
      target: '#product-grid',
      swap: 'innerHTML'
    });

    closeFilterModal();
  });
}

if (clearFilter) {
  clearFilter.addEventListener('click', () => {
    document.querySelectorAll('input[name="category"]').forEach(el => el.checked = false);
    const minIn = document.getElementById('min-price');
    const maxIn = document.getElementById('max-price');
    if (minIn) minIn.value = '';
    if (maxIn) maxIn.value = '';
    if (badge) badge.classList.add('hidden');
  });
}

// --- HTMX shimmer handlers ---
const shimmer = document.getElementById('shimmer-loader');
const grid = document.getElementById('product-grid');
const fade = document.getElementById('fade-overlay');

document.body.addEventListener('htmx:beforeRequest', () => {
  if (grid) grid.classList.add('hidden');
  if (shimmer) shimmer.classList.remove('hidden');
  if (fade) {
    fade.classList.remove('hidden');
    fade.classList.add('opacity-100');
  }
});

document.body.addEventListener('htmx:afterSwap', () => {
  if (shimmer) shimmer.classList.add('hidden');
  if (grid) {
    grid.classList.remove('hidden');
    grid.classList.add('opacity-0');
    setTimeout(() => {
      grid.classList.remove('opacity-0');
      if (fade) {
        fade.classList.add('opacity-0');
        setTimeout(() => { if (fade) fade.classList.add('hidden'); }, 500);
      }
    }, 50);
  }
});
