// dashboard.js — the daily overview.
// One request (/api/reports/dashboard) fills the whole page.

(() => {
  function customerRow(c) {
    return `<a class="list-item" href="customer-profile.html?id=${c.id}">
      <div class="avatar sm">${App.avatarFor(c.fullName, c.gender)}</div>
      <div class="li-main">
        <div class="li-title">${App.escapeHtml(c.fullName)}</div>
        <div class="li-sub">${c.dueDate ? `Due ${App.formatDate(c.dueDate)}` : 'No due date set'}</div>
      </div>
      <div class="li-aside">
        ${App.statusBadge(c.status)}
        <span class="li-amount credit">${App.formatCurrency(c.balance)}</span>
      </div>
    </a>`;
  }

  function overdueRow(c) {
    const days = c.daysOverdue === 1 ? '1 day late' : `${c.daysOverdue} days late`;
    return `<a class="list-item" href="customer-profile.html?id=${c.id}">
      <div class="avatar sm">${App.avatarFor(c.fullName)}</div>
      <div class="li-main">
        <div class="li-title">${App.escapeHtml(c.fullName)}</div>
        <div class="li-sub">Due ${App.formatDate(c.dueDate)} · ${days}</div>
      </div>
      <span class="li-amount credit">${App.formatCurrency(c.balance)}</span>
    </a>`;
  }

  function transactionRow(t) {
    const isCredit = t.type === 'CREDIT';
    return `<a class="list-item" href="customer-profile.html?id=${t.customerId}">
      <div class="li-icon">${isCredit ? App.itemEmoji(t.description) : '💵'}</div>
      <div class="li-main">
        <div class="li-title">${App.escapeHtml(t.description)}</div>
        <div class="li-sub">${App.escapeHtml(t.customerName)} · ${App.formatDateTime(t.createdAt)}</div>
      </div>
      <span class="li-amount ${isCredit ? 'credit' : 'payment'}">
        ${isCredit ? '+' : '−'}${App.formatCurrency(t.amount)}
      </span>
    </a>`;
  }

  function reminderRow(r) {
    return `<a class="list-item" href="reminders.html">
      <div class="li-icon">🔔</div>
      <div class="li-main">
        <div class="li-title">${App.escapeHtml(r.customerName)}</div>
        <div class="li-sub">${App.formatCurrency(r.amount)} · Due ${App.formatDate(r.dueDate)}</div>
      </div>
      ${App.statusBadge(r.urgency)}
    </a>`;
  }

  function renderList(containerId, rows, renderer, emptyEmoji, emptyMessage) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = rows.length
      ? rows.map(renderer).join('')
      : App.emptyState(emptyEmoji, emptyMessage);
  }

  async function load() {
    try {
      const data = await API.reports.dashboard();
      const s = data.summary;

      App.setText('statCustomers', String(s.totalCustomers));
      App.setText('statOutstanding', App.formatCurrency(s.totalOutstanding));
      App.setText('statOverdue', App.formatCurrency(s.totalOverdue));
      App.setText('statPaidThisMonth', App.formatCurrency(s.paidThisMonth));

      App.setText('subCustomers', `${s.customersOwing} owing`);
      App.setText('subOverdue', `${s.customersOverdue} account${s.customersOverdue === 1 ? '' : 's'}`);
      App.setText('subOutstanding', `${s.customersDueToday} due today`);
      App.setText('subPaidThisMonth', `${App.formatCurrency(s.paidToday)} today`);

      renderList('topDebtors', data.topDebtors, customerRow, '🎉', 'Nobody owes you anything.');
      renderList('overdueList', data.overdueCustomers, overdueRow, '✅', 'No overdue accounts.');
      renderList('recentTransactions', data.recentTransactions, transactionRow, '🧾',
        'No transactions yet.');
      renderList('upcomingReminders', data.upcomingReminders, reminderRow, '🔕',
        'No reminders set.');
    } catch (err) {
      App.handleError(err);
      ['topDebtors', 'overdueList', 'recentTransactions', 'upcomingReminders'].forEach((id) => {
        App.setHtml(id, App.emptyState('⚠️', err.message));
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'dashboard') return;
    load();

    // Reload when the owner navigates back after recording something.
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) load();
    });
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) load();
    });
  });
})();
