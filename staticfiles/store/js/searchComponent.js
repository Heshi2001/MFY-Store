// --- Alpine Search Component (GLOBAL) ---
function searchComponent() {
  return {
    desktopOpen: false,
    mobileSheetOpen: false,
    openDesktop() {
      this.desktopOpen = true;
      this.$nextTick(() => document.getElementById('search-box-desktop')?.focus());
    },
    closeDesktop() {
      this.desktopOpen = false;
      document.getElementById('suggestions-desktop')?.classList.add('hidden');
    },
    openMobileSheet() {
      this.mobileSheetOpen = true;
      this.$nextTick(() => document.getElementById('search-box-mobile')?.focus());
    },
    closeMobileSheet() {
      this.mobileSheetOpen = false;
      document.getElementById('suggestions-mobile')?.classList.add('hidden');
    },
    onInput(e, mode) {
      const q = (e.target.value || '').trim();
      if (mode === 'desktop') {
        if (!q) {
          window._searchHelpers.renderSuggestionsHTML('suggestions-desktop', '');
          return;
        }
        window._searchHelpers.desktopFetcher(q);
      } else {
        if (!q) {
          window._searchHelpers.renderSuggestionsHTML('suggestions-mobile', '');
          return;
        }
        this.mobileSheetOpen = true;
        window._searchHelpers.mobileFetcher(q);
      }
    },
    onFocus(mode) {
      const recent = window._searchHelpers.getRecentSearches();
      if (mode === 'desktop') {
        window._searchHelpers.renderSuggestionsHTML('suggestions-desktop', '');
        const el = document.getElementById('suggestions-desktop');
        if (el) el.classList.toggle('hidden', recent.length === 0);
      } else {
        window._searchHelpers.renderSuggestionsHTML('suggestions-mobile', '');
        this.mobileSheetOpen = recent.length > 0;
      }
    }
  };
}

// ✅ Make Alpine see this globally
window.searchComponent = searchComponent;
