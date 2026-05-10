 // ✅ GLOBAL SAFE INIT
window._searchHelpers = window._searchHelpers || {}

function escapeHtml(str){
  if(str === null || str === undefined) return ""
  return String(str).replace(/[&<>"'`=\/]/g,s=>({
    '&':'&amp;',
    '<':'&lt;',
    '>':'&gt;',
    '"':'&quot;',
    "'":'&#39;',
    '/':'&#x2F;',
    '`':'&#x60;',
    '=':'&#x3D;'
  })[s]);
}

/* =========================
   ✅ ALPINE COMPONENT (SAFE)
========================= */
function searchComponent(){
return{

desktopOpen:false,
mobileSheetOpen:false,

init(){
  if(!window._searchHelpers){
    console.warn("Search helpers not ready yet")
  }
},

openDesktop(){
  this.desktopOpen = true

  this.$nextTick(() => {
    const input = document.getElementById("search-box-desktop")
    if(input){
      input.focus()
      input.dispatchEvent(new Event("focus"))
    }
  })
},

closeDesktop(){
  this.desktopOpen=false
  document.getElementById("suggestions-desktop")?.classList.add("hidden")
},

openMobileSheet(){
  this.mobileSheetOpen=true
  this.$nextTick(()=>{
    document.getElementById("search-box-mobile")?.focus()
  })
},

closeMobileSheet(){
  this.mobileSheetOpen=false
  document.getElementById("suggestions-mobile")?.classList.add("hidden")
},

onInput(e,mode){

if(!window._searchHelpers) return 

const q=(e?.target?.value || "").trim()

if(!q){

  if(mode==="desktop"){
    window._searchHelpers.renderSuggestions("suggestions-desktop",[])
    liveSearch("")
  }
  else{
    window._searchHelpers.renderSuggestions("suggestions-mobile",[])
  }

  document.getElementById("live-results")?.replaceChildren()
  document.getElementById("empty-state")?.classList.remove("hidden")

  return
}

if(mode==="desktop"){
  document.getElementById("suggestions-desktop")?.classList.remove("hidden")
  window._searchHelpers.desktopFetcher(q)

  // ✅ Only trigger live results after 2 characters
  if(q.length >= 2){
    liveSearch(q)
  } else {
    document.getElementById("live-results")?.replaceChildren()
  }
}
else{
  this.mobileSheetOpen=true
  document.getElementById("suggestions-mobile")?.classList.remove("hidden")
  window._searchHelpers.mobileFetcher(q)
}
},

onFocus(mode){

if(!window._searchHelpers) return  

const inputId = mode==="desktop" ? "search-box-desktop" : "search-box-mobile"
const containerId = mode==="desktop" ? "suggestions-desktop" : "suggestions-mobile"

const input = document.getElementById(inputId)
const value = (input?.value || "").trim()

if(value.length > 0) return

window._searchHelpers.renderSuggestions(containerId, [])
document.getElementById(containerId)?.classList.remove("hidden")

if(mode==="mobile"){
  this.mobileSheetOpen = true
}

},
handleSubmit(e){
  const input = e.target.querySelector("input[name='query']")
  const query = input?.value?.trim()

  if(!query) return

  // Save search
  if(window._searchHelpers){
    window._searchHelpers.saveRecentSearch(query)
  }

  // Controlled navigation
  window.location.href = `${e.target.action}?query=${encodeURIComponent(query)}`
},
// 🔥 ADD HERE (inside same object)
submitMobileSearch(){
  const input = document.getElementById("search-box-mobile")
  const query = input?.value?.trim()

  if(!query) return

  if(window._searchHelpers){
    window._searchHelpers.saveRecentSearch(query)
  }

 // ✅ get correct Django URL dynamically
  const form = input.closest("form")

  if(form){
    window.location.href = `${form.action}?query=${encodeURIComponent(query)}`
  }
}
}
}

window.searchComponent = searchComponent


/* =========================
   ✅ CORE LOGIC (SAFE)
========================= */

let activeIndex = -1
let liveSearchTimer = null
let lastQuery = "" // 🔥 prevent race condition

function liveSearch(query){

  clearTimeout(liveSearchTimer)
  lastQuery = query

  liveSearchTimer = setTimeout(()=>{

    const resultsContainer = document.getElementById("live-results")
    const emptyState = document.getElementById("empty-state")

    if(!query.trim()){
      resultsContainer?.replaceChildren()
      emptyState?.classList.remove("hidden")
      return
    }

    emptyState?.classList.add("hidden")

    if(resultsContainer){
      resultsContainer.innerHTML = `
        <div class="text-gray-400 text-center py-6">
          Searching...
        </div>
      `
    }

    if(typeof searchAjaxURL === "undefined"){
      console.error("searchAjaxURL is not defined")
      return
    }

    fetch(searchAjaxURL + "?q=" + encodeURIComponent(query))
      .then(res => res.ok ? res.json() : Promise.reject(res))
      .then(data => {

        // 🔥 ignore outdated responses
        if(query !== lastQuery) return

        if(resultsContainer){
          resultsContainer.style.opacity = "0"

          setTimeout(()=>{
            resultsContainer.innerHTML = data?.html || `
              <div class="text-gray-400 text-center py-6">
                No products found
              </div>
            `
            resultsContainer.style.opacity = "1"
          },150)
        }
      })
      .catch(err => {
        console.error("Live search error:", err)

        if(resultsContainer){
          resultsContainer.innerHTML = `
            <div class="text-red-400 text-center py-6">
              Something went wrong
            </div>
          `
        }
      })

  }, 300)
}


/* =========================
   ✅ RECENT SEARCHES (SAFE)
========================= */

function getRecentSearches(){
  try{
    return JSON.parse(localStorage.getItem("recentSearches")||"[]")
  }catch{
    return []
  }
}

function saveRecentSearch(query){
  if(!query) return

  let recent = getRecentSearches()
    .filter(q => q.toLowerCase() !== query.toLowerCase())

  recent.unshift(query)

  if(recent.length > 6) recent = recent.slice(0,6)

  localStorage.setItem("recentSearches",JSON.stringify(recent))
}

function clearRecentSearches(){
  localStorage.removeItem("recentSearches")
}


/* =========================
   ✅ RENDERING (SAFE)
========================= */

function renderSuggestionsHTML(containerId, html){

  const container=document.getElementById(containerId)
  if(!container) return

  container.innerHTML = html || ""

  if(html && html.trim() !== ""){
    container.classList.remove("hidden")

    requestAnimationFrame(()=>{
      container.classList.remove("scale-95","opacity-0")
      container.classList.add("scale-100","opacity-100")
    })
  } 
  else {
    container.classList.add("scale-95","opacity-0")
    setTimeout(()=>{
      container.classList.add("hidden")
    },200)
  }
}


function renderSuggestions(containerId,results=[],fromSearch=false){

  let html=""
  activeIndex = -1

  const recent=getRecentSearches()
  const recentPreview=recent.slice(0,4)

  if(recent.length>0 && !fromSearch){

  html+=`
  <div class="flex items-center justify-between px-4 py-2 border-b border-gray-700 bg-gray-800 text-gray-300 text-sm font-medium">
    <span>Recent Searches</span>
    <button id="clear-recent" class="text-xs text-green-400">Clear All</button>
  </div>

  <div class="divide-y divide-gray-700">
  ${recentPreview.map(q=>`
    <div class="recent-item group px-4 py-2 flex items-center gap-2 cursor-pointer bg-gray-800 hover:bg-gray-700">
      <i class="fas fa-clock text-gray-500"></i>
      <span class="truncate text-gray-300">${escapeHtml(q)}</span>
    </div>
  `).join("")}
  </div>
  `
  }

  if(Array.isArray(results) && results.length>0){

  html+=results.map(item=>`
  <div class="suggestion-item flex items-center gap-3 px-4 py-2 cursor-pointer hover:bg-gray-700"
  data-name="${escapeHtml(item?.name)}"
  data-url="${escapeHtml(item?.url)}">

  <img src="${escapeHtml(item?.image||"/static/img/no-image.png")}"
  class="w-10 h-10 rounded-md object-cover border border-gray-600">

  <div class="flex-1 min-w-0">
    <div class="font-medium text-white truncate">${item?.highlight || escapeHtml(item?.name)}</div>
    <div class="text-sm text-gray-400 truncate">${escapeHtml(item?.category)}</div>
  </div>

  </div>
  `).join("")
  }
  else if(fromSearch){
  html+=`<div class="p-3 text-gray-400 text-sm text-center">No products found</div>`
  }

  renderSuggestionsHTML(containerId, html)

  document.getElementById("clear-recent")?.addEventListener("click",()=>{
    clearRecentSearches()
    renderSuggestions(containerId,[],true)
  })
}


/* =========================
   ✅ FETCHER (SAFE + DEBOUNCED)
========================= */

function makeFetcher(containerId){

let timer=null

return function(query){

clearTimeout(timer)

timer=setTimeout(()=>{

if(!query.trim()){
renderSuggestions(containerId,[],false)
return
}

if(typeof searchSuggestionsURL === "undefined"){
  console.error("searchSuggestionsURL not defined")
  return
}

fetch(searchSuggestionsURL+"?q="+encodeURIComponent(query))
.then(res => res.ok ? res.json() : Promise.reject(res))
.then(data=>{
renderSuggestions(containerId,data,true)
})
.catch(err=>{
console.error("Fetch error:", err)
renderSuggestions(containerId,[],true)
})

},260)

}

}


/* =========================
   ✅ DOM READY
========================= */

document.addEventListener("DOMContentLoaded",()=>{

function hookSuggestionClicks(containerId,inputId){

const container=document.getElementById(containerId)
if(!container) return

container.addEventListener("click",e=>{

const row=e.target.closest(".suggestion-item")
const recent=e.target.closest(".recent-item")

if(row){
saveRecentSearch(row.dataset?.name)
if(row.dataset?.url) window.location.href=row.dataset.url
}

if(recent){
const text=recent.textContent.trim()
const input=document.getElementById(inputId)

if(input) input.value=text

saveRecentSearch(text)

const form=input?.closest("form")
if(form){
    const url = form.action + "?query=" + encodeURIComponent(text)
    window.location.href = url
  }
}

})

}


function hookKeyboard(inputId, containerId){

const input=document.getElementById(inputId)
const container=document.getElementById(containerId)

if(!input || !container) return

input.addEventListener("keydown",e=>{

const items=[...container.querySelectorAll(".suggestion-item, .recent-item")]
if(!items.length) return

if(e.key==="ArrowDown"){
e.preventDefault()
activeIndex=(activeIndex+1)%items.length
}

if(e.key==="ArrowUp"){
e.preventDefault()
activeIndex=(activeIndex-1+items.length)%items.length
}

if(e.key==="Enter"){
if(activeIndex>=0){
e.preventDefault()
items[activeIndex].click()
}
return
}

if(activeIndex >= 0){
const selected = items[activeIndex]
const text = selected.dataset?.name || selected.textContent.trim()
input.value = text
}

items.forEach((el,i)=>el.classList.toggle("bg-gray-700",i===activeIndex))
items[activeIndex]?.scrollIntoView({block:"nearest"})

})

}


document.addEventListener("click", e => {
  ["suggestions-desktop","suggestions-mobile"].forEach(id => {

    const box = document.getElementById(id)
    if (!box) return

    const input = id === "suggestions-desktop"
      ? document.getElementById("search-box-desktop")
      : document.getElementById("search-box-mobile")

    if (!box.contains(e.target) && !(input && input.contains(e.target))) {
      box.classList.add("hidden")
    }
  })
})


const desktopFetcher=makeFetcher("suggestions-desktop")
const mobileFetcher=makeFetcher("suggestions-mobile")

hookSuggestionClicks("suggestions-desktop","search-box-desktop")
hookSuggestionClicks("suggestions-mobile","search-box-mobile")

hookKeyboard("search-box-desktop","suggestions-desktop")
hookKeyboard("search-box-mobile","suggestions-mobile")

// ✅ GLOBAL INIT
window._searchHelpers={
renderSuggestions,
renderSuggestionsHTML,
desktopFetcher,
mobileFetcher,
saveRecentSearch,
getRecentSearches
}

})