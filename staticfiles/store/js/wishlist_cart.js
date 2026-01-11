// Wishlist + Add-to-Cart AJAX
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
// 🩵 Wishlist (Event Delegation)
// ---------------------------
document.body.addEventListener("click", (e) => {
  const btn = e.target.closest(".wishlist-btn");
  if (!btn) return;

  const productId = btn.dataset.productId;
  console.log("Wishlist clicked for product:", productId); // Debug line
  if (!productId) return;

  fetch(`/add_to_wishlist/${productId}/`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrftoken,
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((res) => res.json())
    .then((data) => {
      document.querySelectorAll(`.wishlist-btn[data-product-id="${productId}"]`).forEach((button) => {
        const icon = button.querySelector("i");
        if (!icon) return;
        if (data.added) {
          icon.classList.replace("fa-regular", "fa-solid");
          icon.classList.add("text-[#00C897]");
        } else {
          icon.classList.replace("fa-solid", "fa-regular");
          icon.classList.remove("text-[#00C897]");
        }
      });

      if (data.added) {
        showToast("Added to wishlist ❤️", "success");
      } else {
        showToast("Removed from wishlist 💔", "error");
      }
    })
    .catch(() => showToast("Something went wrong!", "error"));
});

// ---------------------------
// 🛒 Add to Cart (Unchanged)
// ---------------------------
document.body.addEventListener("click", (e) => {
  const btn = e.target.closest(".add-to-cart-btn");
  if (!btn) return;

  e.preventDefault();
  const productId = btn.dataset.productId;
  if (!productId) return;

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
    });
});
