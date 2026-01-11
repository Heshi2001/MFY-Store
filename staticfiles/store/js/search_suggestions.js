function escapeHtml(str) {
  return String(str).replace(/[&<>"'`=\/]/g, s => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '/': '&#x2F;', '`': '&#x60;', '=': '&#x3D;'
  })[s]);
}

document.addEventListener('DOMContentLoaded', () => {

  function hookSuggestionClicks(containerId, inputId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.addEventListener('click', e => {
      const row = e.target.closest('.suggestion-item');
      const recentRow = e.target.closest('.recent-item');
      if (!row && !recentRow) return;
      if (row) {
        const name = row.dataset.name;
        const url = row.dataset.url;
        if (name) saveRecentSearch(name);
        if (url) window.location.href = url;
      } else if (recentRow) {
        const text = recentRow.textContent.trim();
        const input = document.getElementById(inputId);
        if (input) input.value = text;
        saveRecentSearch(text);
        const form = input ? input.closest('form') : null;
        if (form) form.submit();
      }
    });
  }

  function renderSuggestionsHTML(containerId, html) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = html || '';
    container.classList.toggle('hidden', !html || html.trim() === '');
  }

  function getRecentSearches() {
    try {
      return JSON.parse(localStorage.getItem('recentSearches') || '[]');
    } catch {
      return [];
    }
  }

  function saveRecentSearch(query) {
    if (!query) return;
    let recent = getRecentSearches().filter(q => q.toLowerCase() !== query.toLowerCase());
    recent.unshift(query);
    if (recent.length > 6) recent = recent.slice(0, 6);
    localStorage.setItem('recentSearches', JSON.stringify(recent));
  }

  function makeFetcher(containerId) {
    let timer = null;
    return function(query) {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (!query.trim()) {
          renderSuggestionsHTML(containerId, '');
          return;
        }
        fetch(searchSuggestionsURL + "?q=" + encodeURIComponent(query))
          .then(res => res.json())
          .then(data => {
            console.log("Search suggestions response:", data);
            let html = data.map(item => `
              <div class="suggestion-item flex items-center gap-3 p-2 hover:bg-gray-700 cursor-pointer"
                data-name="${escapeHtml(item.name)}"
                data-url="${escapeHtml(item.url)}">
                <img src="${escapeHtml(item.image)}" class="w-10 h-10 object-cover rounded-lg">
                <div>
                  <p class="font-medium text-white">${escapeHtml(item.name)}</p>
                  <p class="text-sm text-gray-400">${escapeHtml(item.category)}</p>
                </div>
              </div>`).join('');
            renderSuggestionsHTML(containerId, html);
          });
      }, 260);
    };
  }

  hookSuggestionClicks('suggestions-desktop', 'search-box-desktop');
  hookSuggestionClicks('suggestions-mobile', 'search-box-mobile');
  const desktopFetcher = makeFetcher('suggestions-desktop');
  const mobileFetcher = makeFetcher('suggestions-mobile');

  window._searchHelpers = {
    renderSuggestionsHTML, desktopFetcher, mobileFetcher, saveRecentSearch, getRecentSearches
  };
});
