// Wishlist + Add-to-Cart AJAX (FINAL PRODUCTION)
console.log("wishlist_cart.js loaded");

// ---------------------------
// Helper: CSRF Cookie
// ---------------------------
const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    document.cookie.split(";").forEach((cookie) => {
      if (cookie.trim().startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.trim().substring(name.length + 1));
      }
    });
  }
  return cookieValue;
};

const csrftoken =
  document.querySelector('meta[name="csrf-token"]')?.content ||
  getCookie("csrftoken");

// ---------------------------
// 🔥 HTMX CSRF FIX
// ---------------------------
document.body.addEventListener("htmx:configRequest", (event) => {
  event.detail.headers["X-CSRFToken"] = csrftoken;
});

// ---------------------------
// Helper: Show Toast
// ---------------------------
function showToast(message, type = "success") {
  const toast = document.getElementById("cart-toast");
  const toastMessage = document.getElementById("cart-toast-message");
  if (!toast || !toastMessage) return;

  toast.classList.remove("bg-green-500", "bg-red-500", "bg-gray-500");

  if (type === "success") toast.classList.add("bg-green-500");
  else if (type === "error") toast.classList.add("bg-red-500");
  else toast.classList.add("bg-gray-500");

  toastMessage.innerText = message;

  toast.classList.remove("hidden", "opacity-0", "translate-y-5");
  toast.classList.add("opacity-100", "translate-y-0", "transition-all", "duration-500", "ease-out");

  setTimeout(() => {
    toast.classList.remove("opacity-100", "translate-y-0");
    toast.classList.add("opacity-0", "translate-y-5");
    setTimeout(() => toast.classList.add("hidden"), 500);
  }, 3000);
}

// ---------------------------
// 💚 Heart Burst Animation
// ---------------------------
function heartBurst(btn) {
  const burst = document.createElement("span");
  burst.className = "absolute inset-0 flex items-center justify-center pointer-events-none";

  for (let i = 0; i < 6; i++) {
    const dot = document.createElement("span");
    dot.className = "absolute w-1.5 h-1.5 bg-[#00C897] rounded-full animate-ping";
    dot.style.transform = `rotate(${i * 60}deg) translateY(-12px)`;
    burst.appendChild(dot);
  }

  btn.appendChild(burst);
  setTimeout(() => burst.remove(), 400);
}

// ---------------------------
// 🩵 Wishlist (FINAL + PAGE AWARE)
// ---------------------------
document.body.addEventListener("click", (e) => {
  const btn = e.target.closest(".wishlist-btn");
  if (!btn) return;

  e.preventDefault();
  e.stopPropagation();

  const productId = btn.dataset.productId;
  if (!productId) return;

  // 🚫 prevent spam click
  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  const isWishlistPage = document.querySelector('[data-page="wishlist"]');
  const isRemoveOnly = btn.classList.contains("remove-only");

  const icon = btn.querySelector("i");

  // ✨ Optimistic UI ONLY for normal pages
  if (!isWishlistPage && icon) {
    icon.classList.toggle("fa-solid");
    icon.classList.toggle("fa-regular");
    icon.classList.toggle("text-[#00C897]");
    icon.classList.add("scale-125");

    heartBurst(btn);

    setTimeout(() => {
      icon.classList.remove("scale-125");
    }, 150);
  }

  const url = APP_URLS.toggleWishlist.replace("0", productId);

  fetch(url, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrftoken,
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then(res => {
      if (res.status === 302 || res.redirected) {
        window.location.href = "/accounts/login/";
        return;
      }
      return res.json();
    })
    .then(data => {
      if (!data) return;

      // 💥 Wishlist Page → Remove Only Behavior
      if (isWishlistPage && isRemoveOnly && !data.added) {
        const card = btn.closest(".group");

        if (card) {
          card.classList.add("opacity-0", "scale-90", "transition", "duration-300");

          setTimeout(() => {
            card.remove();

            const grid = document.getElementById("wishlist-grid");
            const remaining = grid.querySelectorAll(".group");

            if (remaining.length === 0) {
              grid.innerHTML = `
                <div class="col-span-full text-center mt-10 animate-fade-in">
                  <h3 class="text-xl text-gray-300">Your wishlist is empty 😢</h3>
                  <p class="text-gray-500 mt-2">Add items you love!</p>
                  <a href="/products/" 
                     class="inline-block mt-4 px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg transition">
                    Browse Products
                  </a>
                </div>
              `;
            }
          }, 300);
        }

        showToast("💔 Removed from wishlist");
        return;
      }

      // 🔄 Normal Toggle (other pages)
      document
        .querySelectorAll(`.wishlist-btn[data-product-id="${productId}"]`)
        .forEach(button => {
          const i = button.querySelector("i");
          if (!i) return;

          if (data.added) {
            i.classList.remove("fa-regular");
            i.classList.add("fa-solid", "text-[#00C897]");
          } else {
            i.classList.remove("fa-solid", "text-[#00C897]");
            i.classList.add("fa-regular");
          }
        });

      showToast(data.message || "Wishlist updated");
    })
    .catch(() => {
      showToast("Something went wrong!", "error");
    })
    .finally(() => {
      btn.dataset.loading = "false";
    });
});

// ---------------------------
// 🛒 Add to Cart (UNCHANGED)
// ---------------------------
document.body.addEventListener("click", (e) => {
  const btn = e.target.closest(".add-to-cart-btn");
  if (!btn) return;

  e.preventDefault();

  const productId = btn.dataset.productId;
  if (!productId) return;

  if (btn.dataset.loading === "true") return;
  btn.dataset.loading = "true";

  fetch(ADD_TO_CART_URL.replace("0", productId), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken,
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({ product_id: productId, quantity: 1 }),
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        const cartBadge = document.querySelector('a[href="/cart/"] span');
        if (cartBadge) cartBadge.innerText = data.cart_count || 0;

        showToast("Added to cart!", "success");
      } else {
        showToast("Something went wrong!", "error");
      }
    })
    .catch(() => {
      showToast("Something went wrong!", "error");
    })
    .finally(() => {
      btn.dataset.loading = "false";
    });
});

// ---------------------------
// ⚡ HTMX UX (UNCHANGED)
// ---------------------------
document.body.addEventListener("htmx:beforeSwap", (e) => {
  if (e.target.id === "product-grid") {
    e.target.style.opacity = "0.5";
  }
});

document.body.addEventListener("htmx:afterSwap", (e) => {
  if (e.target.id === "product-grid") {
    e.target.style.opacity = "1";
  }
});