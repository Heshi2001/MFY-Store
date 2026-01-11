// search.js
document.addEventListener('DOMContentLoaded', () => {
  const searchBox = document.getElementById("search-box");
  const suggestionsBox = document.getElementById("suggestions");
  if (!searchBox || !suggestionsBox) return;

  let debounceTimer = null;
  let activeIndex = -1;

  const getRecentSearches = () => JSON.parse(localStorage.getItem("recentSearches") || "[]");
  const saveRecentSearch = (query) => {
    if (!query) return;
    let recent = getRecentSearches().filter(q => q.toLowerCase() !== query.toLowerCase());
    recent.unshift(query);
    if (recent.length > 6) recent = recent.slice(0,6);
    localStorage.setItem("recentSearches", JSON.stringify(recent));
  };
  const clearRecentSearches = () => {
    localStorage.removeItem("recentSearches");
    renderSuggestions([], true);
  };

  const renderSuggestions = (results=[], fromSearch=false) => {
    let html = "";
    const recent = getRecentSearches();

    if(recent.length > 0 && !fromSearch){
      html += `<div class="flex items-center justify-between px-4 py-2 border-b bg-gray-50 text-gray-700 font-medium">
                 <span>Recent Searches</span>
                 <button id="clear-recent" class="text-[#006A4E] hover:underline text-sm">Clear All</button>
               </div>
               <div class="divide-y divide-gray-100">
                 ${recent.map(q=>`
                   <div class="recent-item px-4 py-2 flex items-center gap-2 cursor-pointer hover:bg-gray-100">
                     <i class="fas fa-clock text-gray-400"></i>
                     <span class="truncate">${q}</span>
                   </div>`).join("")}
               </div>`;
    }

    if(results.length > 0){
      html += results.map(item=>`
        <div class="suggestion-item flex items-center gap-3 px-4 py-2 cursor-pointer hover:bg-green-50 transition-colors"
             data-name="${item.name}" data-url="${item.url}">
          <img src="${item.image || '/static/img/no-image.png'}" alt="${item.name}" class="w-10 h-10 rounded-md object-cover border flex-shrink-0">
          <div class="flex-1 min-w-0">
            <div class="font-medium text-gray-800 truncate">${item.highlight}</div>
            <div class="text-sm text-gray-500 truncate">${item.category}</div>
          </div>
          <i class="fas fa-search text-gray-400"></i>
        </div>
      `).join("");
    } else if(fromSearch){
      html += `<div class="p-3 text-gray-500 text-sm text-center">No products found</div>`;
    }

    suggestionsBox.innerHTML = html;
    suggestionsBox.classList.toggle("hidden", html.trim() === "");
    document.getElementById("clear-recent")?.addEventListener("click", clearRecentSearches);
  };

  const fetchSuggestions = (query) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (!query.trim()) { renderSuggestions([], false); return; }
      fetch(SEARCH_SUGGESTIONS_URL + "?q=" + encodeURIComponent(query))
        .then(res => res.json())
        .then(data => renderSuggestions(data, true))
        .catch(() => renderSuggestions([], true));
    }, 300);
  };

  searchBox.addEventListener("input", e => fetchSuggestions(e.target.value));
  searchBox.addEventListener("focus", () => { if(!searchBox.value.trim()) renderSuggestions([], false); });

  document.addEventListener("click", e => {
    if(!suggestionsBox.contains(e.target) && e.target !== searchBox) suggestionsBox.classList.add("hidden");
  });

  suggestionsBox.addEventListener("click", e => {
    const suggestion = e.target.closest(".suggestion-item");
    const recentItem = e.target.closest(".recent-item");
    if(e.target.closest("#clear-recent")) return;

    if(suggestion){
      saveRecentSearch(suggestion.dataset.name);
      window.location.href = suggestion.dataset.url;
    } else if(recentItem){
      const text = recentItem.textContent.trim();
      searchBox.value = text;
      saveRecentSearch(text);
      searchBox.closest("form").submit();
    }
  });

  searchBox.addEventListener("keydown", e => {
    const items = Array.from(suggestionsBox.querySelectorAll(".suggestion-item, .recent-item"));
    if(!["ArrowDown","ArrowUp","Enter"].includes(e.key) || items.length===0) return;

    if(e.key==="ArrowDown") activeIndex = (activeIndex+1) % items.length;
    if(e.key==="ArrowUp") activeIndex = (activeIndex-1 + items.length) % items.length;

    if(e.key==="Enter"){
      e.preventDefault();
      if(activeIndex >= 0){
        const selected = items[activeIndex];
        if(selected.classList.contains("suggestion-item")){
          saveRecentSearch(selected.dataset.name);
          window.location.href = selected.dataset.url;
        } else {
          searchBox.value = selected.textContent.trim();
          saveRecentSearch(searchBox.value);
          searchBox.closest("form").submit();
        }
      }
      return;
    }

    items.forEach((item,i)=>item.classList.toggle("bg-green-100", i===activeIndex));
    items[activeIndex]?.scrollIntoView({block:"nearest",behavior:"smooth"});
  });
});
