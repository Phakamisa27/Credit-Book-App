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

  // Same, but leaves off ".00" on whole amounts: R4,200 rather than R4,200.00.
  // Big headline numbers on ThathaCash screens are easier to read this way.
  function formatRands(amount) {
    const full = formatCurrency(amount);
    return full.endsWith('.00') ? full.slice(0, -3) : full;
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

  // A picture for a product, guessed from its name. First match wins.
  function itemEmoji(item) {
    const map = {
      bread: '🍞', milk: '🥛', airtime: '📱', soap: '🧼', sunlight: '🧼',
      toilet: '🧻', maize: '🌽', mealie: '🌽', oil: '🫗', sugar: '🍬', salt: '🧂',
      rice: '🍚', egg: '🥚', biscuit: '🍪', cookie: '🍪', chips: '🍟',
      sweet: '🍬', cola: '🥤', coke: '🥤', fanta: '🥤', sprite: '🥤',
      cooldrink: '🥤', juice: '🧃', water: '💧', tea: '☕', coffee: '☕',
      beans: '🥫', tin: '🥫', fish: '🐟', chicken: '🍗', polony: '🌭',
      flour: '🌾', nappy: '👶', nappies: '👶', washing: '🧺', matches: '🔥',
      uniform: '👕', cement: '🧱', sand: '🏗️',
      paraffin: '🕯️', candle: '🕯️', payment: '💵', cash: '💵',
    };
    const key = String(item || '').toLowerCase();
    for (const k in map) if (key.includes(k)) return map[k];
    return '🛒';
  }

  // ThathaCash stock status pill. The status itself (LOW / GOOD) comes from
  // the server; this only decides the words and colour.
  function stockPill(item) {
    if (item.quantity === 0) return '<span class="tc-pill low">Out of stock</span>';
    if (item.status === 'LOW') return '<span class="tc-pill low">Running low</span>';
    return '<span class="tc-pill good">Good</span>';
  }

  function unitsText(quantity) {
    return `${quantity} unit${quantity === 1 ? '' : 's'}`;
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

  // ----------------------------------------------------------------- icons --
  // Simple line icons, drawn in the current text colour so they turn green
  // when their menu item is active.
  const svg = (paths) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

  const ICONS = {
    home: svg('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h14V9.5"/><path d="M10 20v-6h4v6"/>'),
    stock: svg('<path d="M4.5 8h15l-1.2 12H5.7L4.5 8Z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>'),
    transactions: svg('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 8h6M9 12h6M9 16h3"/>'),
    more: svg('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    logout: svg('<path d="M14 4h5v16h-5"/><path d="M10 8l-4 4 4 4"/><path d="M6 12h10"/>'),
    back: svg('<path d="M15 5l-7 7 7 7"/>'),
    bell: svg('<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15L6 16Z"/><path d="M10 20a2 2 0 0 0 4 0"/>'),
    search: svg('<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/>'),
    chevron: svg('<path d="M9 5l7 7-7 7"/>'),
    share: svg('<circle cx="18" cy="5.5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="18.5" r="2.5"/><path d="m8.2 10.8 7.6-4M8.2 13.2l7.6 4"/>'),
  };

  // The ThathaCash shop mark: a green awning over a shopfront.
  const LOGO_SVG = `<svg class="tc-logo" viewBox="0 0 32 32" aria-hidden="true">
      <rect x="5" y="13" width="22" height="16" rx="2" fill="#0b5d34"/>
      <path d="M3 5h26l-1.5 8.5h-23L3 5Z" fill="#1fa05c"/>
      <path d="M9.5 5 8.8 13.5M16 5v8.5M22.5 5l.7 8.5" stroke="#fff" stroke-width="1.4" opacity=".7"/>
      <rect x="12.5" y="19" width="7" height="10" rx="1" fill="#fff"/>
    </svg>`;

  // ----------------------------------------------------------------- shell --
  // Navigation is generated rather than pasted into every HTML file, so
  // adding a page means editing one array.
  const NAV_ITEMS = [
    { key: 'home', label: 'Home', icon: ICONS.home, href: 'dashboard.html' },
    { key: 'stock', label: 'Stock', icon: ICONS.stock, href: 'stock.html' },
    { key: 'transactions', label: 'Transactions', icon: ICONS.transactions, href: 'transactions.html' },
    { key: 'more', label: 'More', icon: ICONS.more, href: 'settings.html' },
  ];

  // Pages that belong to a menu section without being its own entry.
  // The old Credit Book pages still work by URL; they just sit under "More".
  const NAV_ALIASES = {
    dashboard: 'home',
    order: 'home',
    draws: 'transactions',
    settings: 'more',
    customers: 'more',
    'add-customer': 'more',
    'edit-customer': 'more',
    'customer-profile': 'more',
    'record-credit': 'more',
    reminders: 'more',
    reports: 'more',
  };

  function activeNavKey() {
    const page = document.body.dataset.page;
    return NAV_ALIASES[page] || page;
  }

  function renderSidebar() {
    const active = activeNavKey();
    const user = API.getCachedUser();
    const businessName = (user && user.businessName) || 'Your shop';

    const links = NAV_ITEMS.map(
      (item) => `<a class="side-link ${item.key === active ? 'active' : ''}" href="${item.href}">
        <span class="side-icon">${item.icon}</span><span>${item.label}</span>
      </a>`
    ).join('');

    return `<aside class="sidebar">
      <div class="side-brand">
        <span class="side-brand-mark">${LOGO_SVG}</span>
        <span class="side-brand-text">
          <strong>ThathaCash</strong>
          <small data-bind="businessName">${escapeHtml(businessName)}</small>
        </span>
      </div>
      <nav class="side-nav">${links}</nav>
      <button type="button" class="side-link side-logout" id="sidebarLogout">
        <span class="side-icon">${ICONS.logout}</span><span>Log out</span>
      </button>
    </aside>`;
  }

  // Below 1024px the sidebar is hidden and this bar is the menu.
  function renderBottomNav() {
    const active = activeNavKey();
    const links = NAV_ITEMS.map(
      (item) => `<a class="nav-item ${item.key === active ? 'active' : ''}" href="${item.href}"
          ${item.key === active ? 'aria-current="page"' : ''}>
          <span class="nav-icon">${item.icon}</span>${item.label}
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
        el.textContent = user.businessName || 'Your shop';
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
    ICONS,
    LOGO_SVG,
    formatCurrency,
    formatRands,
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
    stockPill,
    unitsText,
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
