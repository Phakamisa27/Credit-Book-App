// app.js — shared helpers, the navigation shell, and the login guard.
// Loaded by every page.

const App = (() => {
  // ------------------------------------------------------------ formatting --
  // South African Rand: R500.00, R1,250.00, R18,500.00
  function formatCurrency(amount) {
    const n = Number(amount) || 0;
    const negative = n < 0;
    const [whole, cents] = Math.abs(n).toFixed(2).split('.');
    const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${negative ? '-' : ''}R${grouped}.${cents}`;
  }

  const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  // Timestamp -> "01 Aug 2026 · 14:30"
  function formatDateTime(value) {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    return `${day} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()} · ${time}`;
  }

  // YYYY-MM-DD -> "01 Aug 2026", parsed by hand so no timezone shift occurs.
  function formatDate(value) {
    if (!value) return '';
    const [y, m, d] = String(value).slice(0, 10).split('-').map(Number);
    if (!y || !m || !d) return '';
    return `${String(d).padStart(2, '0')} ${MONTHS_SHORT[m - 1]} ${y}`;
  }

  // Short form for tables: "01 Aug"
  function formatDateShort(value) {
    if (!value) return '';
    const [, m, d] = String(value).slice(0, 10).split('-').map(Number);
    if (!m || !d) return '';
    return `${String(d).padStart(2, '0')} ${MONTHS_SHORT[m - 1]}`;
  }

  function todayISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate()
    ).padStart(2, '0')}`;
  }

  // SA mobile format: 074 099 8882 (3-3-4)
  function formatPhoneNumber(value) {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 10);
    if (digits.length <= 3) return digits;
    if (digits.length <= 6) return `${digits.slice(0, 3)} ${digits.slice(3)}`;
    return `${digits.slice(0, 3)} ${digits.slice(3, 6)} ${digits.slice(6)}`;
  }

  function bindPhoneInput(input) {
    if (!input) return;
    input.addEventListener('input', () => {
      input.value = formatPhoneNumber(input.value);
    });
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  // --------------------------------------------------------------- badges --
  const STATUS_LABELS = {
    PAID: 'PAID',
    OWING: 'OWING',
    OVERDUE: 'OVERDUE',
    OVERDUE_REMINDER: 'OVERDUE',
    DUE_TODAY: 'DUE TODAY',
    DUE_SOON: 'DUE SOON',
    UPCOMING: 'UPCOMING',
    CLOSED: 'DONE',
    PENDING: 'PENDING',
    SENT: 'SENT',
    DONE: 'DONE',
    CANCELLED: 'CANCELLED',
  };

  const STATUS_CLASSES = {
    PAID: 'status-paid',
    OWING: 'status-owing',
    OVERDUE: 'status-overdue',
    DUE_TODAY: 'status-due-today',
    DUE_SOON: 'status-due-soon',
    UPCOMING: 'status-not-due',
    CLOSED: 'status-paid',
    PENDING: 'status-owing',
    SENT: 'status-not-due',
    DONE: 'status-paid',
    CANCELLED: 'status-paid',
  };

  function statusBadge(status) {
    if (!status) return '';
    const key = String(status).toUpperCase();
    const cls = STATUS_CLASSES[key] || 'status-paid';
    return `<span class="status-badge ${cls}">${escapeHtml(STATUS_LABELS[key] || key)}</span>`;
  }

  // ---------------------------------------------------------------- avatar --
  // Derived from gender when known, otherwise from a hash of the name so the
  // same customer always gets the same face.
  function avatarFor(name, gender) {
    const male = ['👨🏾', '👨🏽', '👴🏾'];
    const female = ['👩🏾', '👩🏽', '👵🏾', '🧕🏾'];
    const mixed = [...male, ...female, '🧑🏾'];
    let sum = 0;
    for (const ch of name || 'x') sum += ch.charCodeAt(0);
    if (gender === 'male') return male[sum % male.length];
    if (gender === 'female') return female[sum % female.length];
    return mixed[sum % mixed.length];
  }

  // ---------------------------------------------------------- line items --
  // Renders a credit's line items as an indented breakdown under its
  // description. Shared so the feed and the customer profile look the same.
  //
  //     Bread      ×2    R30.00
  //     Perfume    ×1   R120.00
  function itemLinesHtml(items) {
    if (!Array.isArray(items) || items.length === 0) return '';
    const rows = items
      .map(
        (i) => `<li class="tx-item">
          <span class="tx-item-name">${escapeHtml(i.name)}</span>
          <span class="tx-item-qty">×${i.quantity}</span>
          <span class="tx-item-unit">@ ${formatCurrency(i.unitPrice)}</span>
          <span class="tx-item-total">${formatCurrency(i.lineTotal)}</span>
        </li>`
      )
      .join('');
    return `<ul class="tx-items">${rows}</ul>`;
  }

  function itemEmoji(item) {
    const map = {
      bread: '🍞', milk: '🥛', airtime: '📱', soap: '🧼', toilet: '🧻',
      maize: '🌽', oil: '🛢️', sugar: '🍬', rice: '🍚', egg: '🥚',
      uniform: '👕', cement: '🧱', sand: '🏗️', cooldrink: '🥤',
      paraffin: '🕯️', candle: '🕯️', payment: '💵', cash: '💵',
    };
    const key = String(item || '').toLowerCase();
    for (const k in map) if (key.includes(k)) return map[k];
    return '🛒';
  }

  // ----------------------------------------------------------------- toast --
  function toast(message, variant = 'info') {
    let el = document.querySelector('.toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'toast';
      el.setAttribute('role', 'status');
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.dataset.variant = variant;
    requestAnimationFrame(() => el.classList.add('show'));
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('show'), 2600);
  }

  const toastError = (message) => toast(message, 'error');
  const toastSuccess = (message) => toast(message, 'success');

  // Every page's catch block funnels through here.
  function handleError(err) {
    console.error(err);
    toastError((err && err.message) || 'Something went wrong. Please try again.');
  }

  // ------------------------------------------------------------------ DOM --
  function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function setHtml(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
  }

  function emptyState(emoji, message, actionHtml = '') {
    return `<div class="empty"><span class="emoji">${emoji}</span>
      <p>${escapeHtml(message)}</p>${actionHtml}</div>`;
  }

  const loadingState = (message = 'Loading…') =>
    `<div class="empty"><span class="emoji">⏳</span><p>${escapeHtml(message)}</p></div>`;

  // Disables a submit button while a request is in flight so a double-tap
  // cannot record the same credit twice.
  async function withBusy(button, fn) {
    if (!button) return fn();
    const original = button.textContent;
    button.disabled = true;
    button.textContent = 'Please wait…';
    try {
      return await fn();
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  // ----------------------------------------------------------------- shell --
  // Navigation is generated rather than pasted into 13 HTML files, so adding
  // a page means editing one array.
  // `short` is what the bottom bar uses — six items on a 360px phone leaves
  // about 58px each, which "Transactions" does not fit into.
  const NAV_ITEMS = [
    { key: 'dashboard', label: 'Dashboard', short: 'Home', icon: '🏠', href: 'dashboard.html' },
    { key: 'customers', label: 'Customers', short: 'Customers', icon: '👥', href: 'customers.html' },
    { key: 'transactions', label: 'Transactions', short: 'History', icon: '📋', href: 'transactions.html' },
    { key: 'reminders', label: 'Reminders', short: 'Reminders', icon: '🔔', href: 'reminders.html' },
    { key: 'reports', label: 'Reports', short: 'Reports', icon: '📊', href: 'reports.html' },
    { key: 'settings', label: 'Settings', short: 'Settings', icon: '⚙️', href: 'settings.html' },
  ];

  // Pages that are part of a section but are not the section's own nav entry.
  const NAV_ALIASES = {
    'add-customer': 'customers',
    'edit-customer': 'customers',
    'customer-profile': 'customers',
    'record-credit': 'transactions',
  };

  function activeNavKey() {
    const page = document.body.dataset.page;
    return NAV_ALIASES[page] || page;
  }

  function renderSidebar() {
    const active = activeNavKey();
    const user = API.getCachedUser();
    const businessName = (user && user.businessName) || 'Credit Book';

    const links = NAV_ITEMS.map(
      (item) => `<a class="side-link ${item.key === active ? 'active' : ''}" href="${item.href}">
        <span class="side-icon">${item.icon}</span><span>${item.label}</span>
      </a>`
    ).join('');

    return `<aside class="sidebar">
      <div class="side-brand">
        <span class="side-brand-mark">📗</span>
        <span class="side-brand-text">
          <strong>${escapeHtml(businessName)}</strong>
          <small>Credit Book</small>
        </span>
      </div>
      <nav class="side-nav">${links}</nav>
      <button type="button" class="side-link side-logout" id="sidebarLogout">
        <span class="side-icon">🚪</span><span>Logout</span>
      </button>
    </aside>`;
  }

  // Settings is on the bar too: below 1024px the sidebar is hidden, so this is
  // the only route to the account screen — and to the Logout button on it.
  function renderBottomNav() {
    const active = activeNavKey();
    const links = NAV_ITEMS.map(
      (item) => `<a class="nav-item ${item.key === active ? 'active' : ''}" href="${item.href}">
          <span class="nav-icon">${item.icon}</span>${item.short}
        </a>`
    ).join('');
    return `<nav class="bottom-nav">${links}</nav>`;
  }

  function initShell() {
    const shell = document.getElementById('appShell');
    if (shell) {
      shell.insertAdjacentHTML('afterbegin', renderSidebar());
    }

    // Only the signed-in pages get the nav bar. On landing/login/register every
    // tab would just bounce back to login, and the bar overlaps the form.
    if (isProtectedPage() && !document.querySelector('.bottom-nav')) {
      document.body.insertAdjacentHTML('beforeend', renderBottomNav());
    }

    document.getElementById('sidebarLogout')?.addEventListener('click', logout);
    document.querySelectorAll('[data-action="logout"]').forEach((btn) => {
      btn.addEventListener('click', logout);
    });
  }

  async function logout() {
    await API.auth.logout();
    window.location.href = 'login.html';
  }

  function isProtectedPage() {
    return document.body.dataset.protected !== undefined;
  }

  // Pages marked data-protected send the owner to login if there is no token.
  // The server enforces this too — this only avoids a flash of empty UI.
  function guard() {
    if (!isProtectedPage()) return true;
    if (!API.isLoggedIn()) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  }

  // Refreshes the cached user so the sidebar shows the real business name.
  async function syncUser() {
    if (!API.isLoggedIn()) return null;
    try {
      const user = await API.auth.me();
      API.setSession(API.getToken(), user);
      document.querySelectorAll('[data-bind="businessName"]').forEach((el) => {
        el.textContent = user.businessName || 'Credit Book';
      });
      return user;
    } catch (_) {
      return null;
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!guard()) return;
    initShell();
    if (isProtectedPage()) syncUser();
  });

  return {
    formatCurrency,
    formatDate,
    formatDateShort,
    formatDateTime,
    formatPhoneNumber,
    bindPhoneInput,
    todayISO,
    escapeHtml,
    statusBadge,
    avatarFor,
    itemEmoji,
    itemLinesHtml,
    toast,
    toastError,
    toastSuccess,
    handleError,
    getParam,
    setText,
    setHtml,
    emptyState,
    loadingState,
    withBusy,
    logout,
  };
})();
