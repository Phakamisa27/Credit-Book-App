// app.js — shared helpers, formatting, navigation, dashboard rendering

const App = (() => {
  // Reusable South African Rand formatter.
  // e.g. 0 -> "R0.00", 25 -> "R25.00", 1250 -> "R1250.00"
  function formatCurrency(amount) {
    return `R${(Number(amount) || 0).toFixed(2)}`;
  }

  const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function formatDate(dateStr) {
    const d = new Date(dateStr);
    const day = d.getDate().toString().padStart(2, '0');
    const time = d.toTimeString().slice(0, 5);
    return `${day} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()} · ${time}`;
  }

  // Format YYYY-MM-DD due dates without timezone shift.
  function formatDueDate(dateStr) {
    if (!dateStr) return '';
    const [y, m, d] = dateStr.split('-').map(Number);
    const day = String(d).padStart(2, '0');
    return `${day} ${MONTHS_SHORT[m - 1]} ${y}`;
  }

  function statusBadge(status) {
    const map = {
      'Not Due': 'status-not-due',
      'Due Today': 'status-due-today',
      Overdue: 'status-overdue',
      Paid: 'status-paid',
    };
    const cls = map[status];
    if (!cls) return '';
    const label =
      status === 'Not Due'
        ? 'NOT DUE'
        : status === 'Due Today'
          ? 'DUE TODAY'
          : status === 'Overdue'
            ? 'OVERDUE'
            : 'PAID';
    return `<span class="status-badge ${cls}">${label}</span>`;
  }

  function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
  }

  // South African mobile format: 074 099 8882 (3-3-4)
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

  // Derive avatar emoji from gender when set, otherwise from name hash.
  function avatarFor(name, gender) {
    const maleEmojis = ['👨🏾', '👨🏽', '👴🏾'];
    const femaleEmojis = ['👩🏾', '👩🏽', '👵🏾', '🧕🏾'];
    const mixedEmojis = [...maleEmojis, ...femaleEmojis, '🧑🏾'];
    let sum = 0;
    for (const ch of name || 'x') sum += ch.charCodeAt(0);
    if (gender === 'male') return maleEmojis[sum % maleEmojis.length];
    if (gender === 'female') return femaleEmojis[sum % femaleEmojis.length];
    return mixedEmojis[sum % mixedEmojis.length];
  }

  function itemEmoji(item) {
    const map = {
      bread: '🍞', milk: '🥛', airtime: '📱', soap: '🧼', toilet: '🧻',
      maize: '🌽', oil: '🛢️', sugar: '🍬', rice: '🍚', egg: '🥚',
      payment: '💵', cash: '💵',
    };
    const key = (item || '').toLowerCase();
    for (const k in map) if (key.includes(k)) return map[k];
    return '🛒';
  }

  function toast(message) {
    let el = document.querySelector('.toast');
    if (!el) {
      el = document.createElement('div');
      el.className = 'toast';
      document.body.appendChild(el);
    }
    el.textContent = message;
    requestAnimationFrame(() => el.classList.add('show'));
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('show'), 2200);
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  // Highlight the active bottom-nav item based on data-page
  function initNav() {
    const page = document.body.dataset.page;
    document.querySelectorAll('.nav-item').forEach((item) => {
      if (item.dataset.nav === page) item.classList.add('active');
    });
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  // ---- Dashboard (dashboard.html) ----
  function applyProfileToHero(profile) {
    const hero = document.getElementById('heroCard');

    if (profile?.businessName) {
      setText('heroTitle', profile.businessName);
      setText('heroSub', 'Track customer credit with ease');
      if (hero) hero.dataset.state = 'active';
    } else {
      setText('heroTitle', 'Welcome to Credit Book');
      setText('heroSub', 'Create your business profile to get started');
      if (hero) hero.dataset.state = 'welcome';
    }

    renderProfileAvatar(profile);
  }

  function renderProfileAvatar(profile) {
    const img = document.getElementById('heroAvatarImg');
    const defaultEl = document.getElementById('heroAvatarDefault');
    if (!img || !defaultEl) return;

    if (profile?.profileImage) {
      img.src = profile.profileImage;
      img.alt = profile.businessName
        ? `${profile.businessName} profile photo`
        : 'Business profile photo';
      img.hidden = false;
      defaultEl.hidden = true;
    } else {
      img.removeAttribute('src');
      img.alt = '';
      img.hidden = true;
      defaultEl.hidden = false;
    }
  }

  function renderDashboardStats() {
    setText('totalOutstanding', formatCurrency(Storage.getTotalOutstanding()));
    setText('todayCredit', formatCurrency(Storage.getTodayCredit()));
    setText('todayPayments', formatCurrency(Storage.getTodayPayments()));
    setText('dueTodayCount', String(Storage.getDueTodayCount()));
    setText('overdueCount', String(Storage.getOverdueCount()));
  }

  async function renderDashboard() {
    try {
      const [profile, customers] = await Promise.all([
        API.getBusinessProfile(),
        API.getCustomers(),
      ]);
      Storage.syncBusinessProfileFromApi(profile);
      Storage.syncCustomersFromApi(customers);
      Storage.recomputeBalances();
      applyProfileToHero(profile);
    } catch (err) {
      toast(err.message || API.OFFLINE_MSG);
      applyProfileToHero(null);
    }

    renderDashboardStats();
  }

  function initProfileUpload() {
    const input = document.getElementById('heroAvatarInput');
    const uploadBtn = document.getElementById('heroAvatarUpload');

    uploadBtn?.addEventListener('click', (e) => {
      e.stopPropagation();
      input?.click();
    });

    input?.addEventListener('change', async () => {
      const file = input.files?.[0];
      if (!file) return;

      if (!file.type.startsWith('image/')) {
        toast('Please select an image file');
        input.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = async () => {
        try {
          let profile = await API.getBusinessProfile();
          if (!profile?.businessName) {
            toast('Create your business profile first');
            return;
          }
          profile = await API.updateBusinessProfile({ profileImage: reader.result });
          Storage.syncBusinessProfileFromApi(profile);
          applyProfileToHero(profile);
          toast('Profile photo saved');
        } catch (err) {
          toast(err.message || API.OFFLINE_MSG);
        }
      };
      reader.onerror = () => {
        toast('Could not read that image');
      };
      reader.readAsDataURL(file);
      input.value = '';
    });
  }

  async function setupBusinessProfile() {
    let current = null;
    try {
      current = await API.getBusinessProfile();
    } catch (err) {
      toast(err.message || API.OFFLINE_MSG);
      return;
    }

    const businessName = prompt('Business name:', current?.businessName || '');
    if (businessName === null) return;
    if (!businessName.trim()) {
      toast('Business name is required');
      return;
    }
    const ownerName = prompt('Owner name:', current?.ownerName || '') || '';
    const phone = prompt('Business phone:', current?.phone || '') || '';

    if (!current && !phone.trim()) {
      toast('Business phone is required');
      return;
    }

    try {
      const payload = {
        businessName: businessName.trim(),
        ownerName: ownerName.trim() || businessName.trim(),
        phone: phone.trim(),
      };
      const profile = current
        ? await API.updateBusinessProfile(payload)
        : await API.createBusinessProfile(payload);
      Storage.syncBusinessProfileFromApi(profile);
      toast('Business profile saved');
      applyProfileToHero(profile);
    } catch (err) {
      toast(err.message || API.OFFLINE_MSG);
    }
  }

  function initDashboard() {
    renderDashboard();
    initProfileUpload();

    document.getElementById('heroText')?.addEventListener('click', setupBusinessProfile);
    document.getElementById('heroText')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setupBusinessProfile();
      }
    });
  }

  function init() {
    initNav();
    if (document.body.dataset.page === 'dashboard') {
      initDashboard();
      // Recalculate when returning to the dashboard (e.g. via back/forward
      // cache after adding a customer, recording credit, or taking a payment).
      window.addEventListener('pageshow', renderDashboard);
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) renderDashboard();
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);

  return {
    formatCurrency,
    formatDate,
    formatDueDate,
    formatPhoneNumber,
    bindPhoneInput,
    getParam,
    avatarFor,
    itemEmoji,
    statusBadge,
    toast,
    escapeHtml,
    setText,
  };
})();
