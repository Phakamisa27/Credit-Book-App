// auth.js — login, register, and the landing page.

(() => {
  function showError(el, message) {
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
  }

  function hideError(el) {
    if (el) el.hidden = true;
  }

  // ------------------------------------------------- show/hide password --
  // Typing a password blind on a phone keyboard is how people end up locked
  // out of their own books. This is purely a browser-side switch between
  // input type="password" and type="text" — nothing about it is sent to the
  // server, so the API is unchanged.
  //
  // The buttons are injected rather than written into both pages, so the SVG
  // exists once. Without JavaScript the fields simply stay masked, which is
  // the safe default.
  const EYE_OPEN = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"
        stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8" />
    </svg>`;

  const EYE_CLOSED = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M2.5 12S6 5.5 12 5.5c1.4 0 2.7.35 3.85.92M21.5 12s-1.4 2.6-4 4.35
               M9.9 9.9a3 3 0 0 0 4.2 4.2"
        stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <path d="m4 4 16 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </svg>`;

  function initPasswordToggles() {
    document.querySelectorAll('.login-field input[type="password"]').forEach((input) => {
      const button = document.createElement('button');
      // Not a submit button — inside a form the default type would submit it.
      button.type = 'button';
      button.className = 'login-field-toggle';
      button.innerHTML = EYE_OPEN;
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', 'Show password');
      button.title = 'Show password';
      if (input.id) button.setAttribute('aria-controls', input.id);

      input.insertAdjacentElement('afterend', button);

      button.addEventListener('click', () => {
        const reveal = input.type === 'password';

        // Changing `type` moves the caret to the end, which is maddening
        // mid-word. Put it back where it was.
        const start = input.selectionStart;
        const end = input.selectionEnd;

        input.type = reveal ? 'text' : 'password';
        button.innerHTML = reveal ? EYE_CLOSED : EYE_OPEN;
        button.setAttribute('aria-pressed', String(reveal));

        const label = reveal ? 'Hide password' : 'Show password';
        button.setAttribute('aria-label', label);
        button.title = label;

        input.focus();
        if (start !== null) {
          try {
            input.setSelectionRange(start, end);
          } catch (_) {
            // Some browsers refuse setSelectionRange right after a type
            // change; the caret lands at the end, which is harmless.
          }
        }
      });
    });
  }

  // ---------------------------------------------------------------- login --
  function initLogin() {
    const form = document.getElementById('loginForm');
    if (!form) return;

    // Already signed in? Skip the form.
    if (API.isLoggedIn()) {
      window.location.replace('dashboard.html');
      return;
    }

    const errorEl = document.getElementById('authError');

    // Once the owner has an account there is no reason to advertise sign-up.
    API.auth
      .status()
      .then(({ accountExists }) => {
        document.querySelectorAll('[data-when="no-account"]').forEach((el) => {
          el.hidden = accountExists;
        });
      })
      .catch(() => {
        // Server unreachable — leave the register link visible.
      });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError(errorEl);

      const email = form.email.value.trim();
      const password = form.password.value;

      if (!email) return showError(errorEl, 'Please enter your email address.');
      if (!password) return showError(errorEl, 'Please enter your password.');

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.auth.login(email, password);
          window.location.href = 'dashboard.html';
        } catch (err) {
          showError(errorEl, err.message);
        }
      });
    });
  }

  // ------------------------------------------------------------- register --
  function initRegister() {
    const form = document.getElementById('registerForm');
    if (!form) return;

    if (API.isLoggedIn()) {
      window.location.replace('dashboard.html');
      return;
    }

    const errorEl = document.getElementById('authError');
    App.bindPhoneInput(form.businessPhone);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError(errorEl);

      const fullName = form.fullName.value.trim();
      const email = form.email.value.trim();
      const businessName = form.businessName.value.trim();
      const businessPhone = form.businessPhone.value.trim();
      const password = form.password.value;
      const confirmPassword = form.confirmPassword.value;

      if (!fullName) return showError(errorEl, 'Please enter your full name.');
      if (!email) return showError(errorEl, 'Please enter your email address.');
      if (password.length < 8) {
        return showError(errorEl, 'Password must be at least 8 characters.');
      }
      if (password !== confirmPassword) {
        return showError(errorEl, 'Passwords do not match.');
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.auth.register({
            fullName,
            email,
            password,
            confirmPassword,
            businessName,
            businessPhone,
          });
          window.location.href = 'dashboard.html';
        } catch (err) {
          showError(errorEl, err.message);
        }
      });
    });
  }

  // -------------------------------------------------------------- landing --
  function initLanding() {
    const primary = document.getElementById('primaryBtn');
    const secondary = document.getElementById('secondaryBtn');
    if (!primary) return;

    if (API.isLoggedIn()) {
      primary.textContent = 'Go to Dashboard';
      primary.href = 'dashboard.html';
      if (secondary) secondary.hidden = true;
    } else {
      primary.textContent = 'Login';
      primary.href = 'login.html';
      if (secondary) {
        secondary.textContent = 'Create an account';
        secondary.href = 'register.html';
        secondary.hidden = false;
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    if (page === 'login') initLogin();
    if (page === 'register') initRegister();
    if (page === 'landing') initLanding();
    if (page === 'login' || page === 'register') initPasswordToggles();
  });
})();
