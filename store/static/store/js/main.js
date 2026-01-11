// --- Your existing main logic ---
document.addEventListener('DOMContentLoaded', () => {
  // ---------------------------
  // Auto-adjust banner padding for fixed navbar
  // ---------------------------
  const navbar = document.querySelector('nav');
  if (navbar) {
    const navbarHeight = navbar.offsetHeight;
    document.documentElement.style.setProperty('--navbar-height', `${navbarHeight}px`);
  }

  // ---------------------------
  // Helper Functions
  // ---------------------------
  const getCookie = name => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      document.cookie.split(';').forEach(cookie => {
        if (cookie.trim().startsWith(name + '=')) {
          cookieValue = decodeURIComponent(cookie.trim().substring(name.length + 1));
        }
      });
    }
    return cookieValue;
  };

  const openSubList = el => {
    el.classList.remove('hidden');
    el.style.maxHeight = el.scrollHeight + 'px';
    el.addEventListener('transitionend', function handler() {
      el.style.maxHeight = 'none';
      el.removeEventListener('transitionend', handler);
    });
  };

  const closeSubList = el => {
    el.style.maxHeight = el.scrollHeight + 'px';
    void el.offsetHeight;
    el.style.maxHeight = '0px';
    el.addEventListener('transitionend', function handler() {
      el.classList.add('hidden');
      el.style.maxHeight = null;
      el.removeEventListener('transitionend', handler);
    });
  };

  const getNodeKey = btn => btn.closest('li').querySelector('a[href]')?.getAttribute('href');
  const saveOpenStates = () => {
    const openNodes = Array.from(document.querySelectorAll('.sub-list:not(.hidden)'))
      .map(el => getNodeKey(el.closest('li').querySelector('.toggle-sub')))
      .filter(Boolean);
    localStorage.setItem('categoryTreeOpen', JSON.stringify(openNodes));
  };
  const restoreOpenStates = () => {
    const openNodes = JSON.parse(localStorage.getItem('categoryTreeOpen') || '[]');
    openNodes.forEach(key => {
      const btn = document.querySelector(`a[href="${key}"]`)?.closest('li')?.querySelector('.toggle-sub');
      if (btn) {
        const listWrapper = btn.closest('li').querySelector('.sub-list');
        const icon = btn.querySelector('svg');
        if (listWrapper) {
          listWrapper.classList.remove('hidden');
          listWrapper.style.maxHeight = 'none';
          icon?.classList.add('rotate-90');
        }
      }
    });
  };

  const closeSiblings = currentLi => {
    const siblings = currentLi.parentElement?.querySelectorAll(':scope > li > .sub-list:not(.hidden)') || [];
    siblings.forEach(sub => {
      if (sub.closest('li') !== currentLi) {
        const siblingBtn = sub.closest('li').querySelector('.toggle-sub');
        siblingBtn?.querySelector('svg')?.classList.remove('rotate-90');
        closeSubList(sub);
      }
    });
  };

  const expandParents = link => {
    let parent = link.closest('.sub-list');
    while (parent) {
      const toggleBtn = parent.previousElementSibling?.querySelector('.toggle-sub');
      const icon = toggleBtn?.querySelector('svg');
      if (toggleBtn) {
        parent.classList.remove('hidden');
        parent.style.maxHeight = 'none';
        icon?.classList.add('rotate-90');
        toggleBtn.closest('li')?.querySelector('div')?.classList.add('open');
      }
      parent = parent.closest('.sub-list');
    }
  };

  // ---------------------------
  // Sidebar
  // ---------------------------
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const closeBtn = document.getElementById('close-btn');
  const openBtn = document.getElementById('menu-btn');

  function openSidebar() {
    sidebar.classList.remove('-translate-x-full');
    overlay.classList.remove('opacity-0', 'pointer-events-none');
    overlay.classList.add('opacity-100');
  }

  function closeSidebar() {
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('opacity-0', 'pointer-events-none');
    overlay.classList.remove('opacity-100');
  }

  if (openBtn) openBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (overlay) overlay.addEventListener('click', closeSidebar);

  // ---------------------------
  // Collapsible Categories
  // ---------------------------
  document.addEventListener('click', e => {
    const btn = e.target.closest('.toggle-sub');
    if (!btn) return;
    const li = btn.closest('li');
    const listWrapper = li.querySelector('.sub-list');
    if (!listWrapper) return;

    if (listWrapper.classList.contains('hidden')) {
      closeSiblings(li);
      btn.querySelector('svg')?.classList.add('rotate-90');
      openSubList(listWrapper);
      li.querySelector('div')?.classList.add('open');
    } else {
      btn.querySelector('svg')?.classList.remove('rotate-90');
      closeSubList(listWrapper);
      li.querySelector('div')?.classList.remove('open');
    }
    setTimeout(saveOpenStates, 400);
  });

  // Highlight active category
  document.addEventListener('click', e => {
    const link = e.target.closest('.sub-list a, ul a');
    if (!link) return;

    document.querySelectorAll('.text-green-400').forEach(a => a.classList.replace('text-green-400', 'text-gray-200'));
    link.classList.replace('text-gray-200', 'text-green-400');
    expandParents(link);
    setTimeout(saveOpenStates, 400);
  });

  restoreOpenStates();
  document.querySelector('.text-green-400') && expandParents(document.querySelector('.text-green-400'));

  // ---------------------------
  // Mobile menu toggle
  // ---------------------------
  document.getElementById("mobile-menu-button")?.addEventListener("click", () => {
    document.getElementById("mobile-menu")?.classList.toggle("hidden");
  });
});
