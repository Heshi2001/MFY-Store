document.addEventListener("DOMContentLoaded", () => {

  /* =====================================================
     TAB SWITCHING
  ===================================================== */
  const buttons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll("[data-tab-panel]");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;

      // Active button
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Panels
      panels.forEach((panel) => {
        const match = panel.dataset.tabPanel === tab;
        panel.classList.toggle("hidden", !match);
        panel.classList.toggle("show", match);
      });

      updateAuthHeader(tab);
    });
  });

  /* =====================================================
     AUTH HEADER
  ===================================================== */
  const header = document.getElementById("authHeader");
  const title = document.getElementById("authHeaderTitle");
  const subtitle = document.getElementById("authHeaderSubtitle");

  function updateAuthHeader(tab) {
    if (!header || !title || !subtitle) return;

    header.classList.add("fade");

    setTimeout(() => {
      if (tab === "login") {
        title.textContent = "Welcome Back";
        subtitle.textContent = "Login to continue to MFY Store";
      } else if (tab === "signup") {
        title.textContent = "Create Account";
        subtitle.textContent = "Join MFY Store today";
      } else if (tab === "otp") {
        title.textContent = "Secure OTP Login";
        subtitle.textContent = "Sign in quickly using a one-time password";
      }

      header.classList.remove("fade");
    }, 180);
  }

  /* =====================================================
     INITIAL STATE (BACKEND SYNC)
     ⚠️ READ ONLY — NO CLICK
  ===================================================== */
  const initialActiveBtn = document.querySelector(".tab-btn.active");
  if (initialActiveBtn) {
    updateAuthHeader(initialActiveBtn.dataset.tab);
  }

  /* =====================================================
     PASSWORD TOGGLE (CLICK + HOLD)
  ===================================================== */
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;

    const show = () => {
      input.type = "text";
      btn.classList.add("active");
      btn.setAttribute("aria-pressed", "true");
    };

    const hide = () => {
      input.type = "password";
      btn.classList.remove("active");
      btn.setAttribute("aria-pressed", "false");
    };

    // Click toggle (desktop)
    btn.addEventListener("click", () => {
      input.type === "password" ? show() : hide();
    });

    // Hold to view (mobile)
    btn.addEventListener("touchstart", show);
    btn.addEventListener("touchend", hide);
    btn.addEventListener("mouseleave", hide);
  });

  /* =====================================================
     PASSWORD STRENGTH METER
  ===================================================== */
  document.querySelectorAll("input[type='password']").forEach((input) => {
    const meter = input.closest(".floating-group")?.querySelector(".meter-bar");
    if (!meter) return;

    input.addEventListener("input", () => {
      const val = input.value;
      let score = 0;

      if (val.length >= 8) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      meter.className = "meter-bar";

      if (score <= 1) {
        meter.style.width = "25%";
        meter.classList.add("meter-weak");
      } else if (score <= 3) {
        meter.style.width = "60%";
        meter.classList.add("meter-medium");
      } else {
        meter.style.width = "100%";
        meter.classList.add("meter-strong");
      }
    });
  });

  /* =====================================================
     PASSWORD MATCH CHECK
  ===================================================== */
  const p1 = document.getElementById("id_password1");
  const p2 = document.getElementById("id_password2");
  const matchText = document.querySelector(".password-match");

  if (p1 && p2 && matchText) {
    p2.addEventListener("input", () => {
      if (!p2.value) {
        matchText.classList.add("hidden");
        return;
      }

      matchText.classList.remove("hidden");

      if (p1.value === p2.value) {
        matchText.textContent = "✓ Passwords match";
        matchText.className =
          "password-match text-sm mt-2 text-green-400";
      } else {
        matchText.textContent = "✗ Passwords do not match";
        matchText.className =
          "password-match text-sm mt-2 text-red-400";
      }
    });
  }

});
