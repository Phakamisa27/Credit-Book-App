// reports.js — business summary, top debtors, overdue accounts, daily activity.

(() => {
  // A plain CSS bar chart. Credit vs payments per day is two numbers a day —
  // a charting library would be more bytes than the whole page.
  function renderActivityChart(days) {
    const chart = document.getElementById('activityChart');
    if (!chart) return;

    const withActivity = days.filter((d) => d.credit > 0 || d.payments > 0);
    if (withActivity.length === 0) {
      chart.innerHTML = App.emptyState('📊', 'No activity in this period.');
      return;
    }

    const max = Math.max(...withActivity.map((d) => Math.max(d.credit, d.payments)));

    chart.innerHTML = `<div class="chart-bars">${withActivity
      .map((d) => {
        const creditHeight = max ? Math.round((d.credit / max) * 100) : 0;
        const paymentHeight = max ? Math.round((d.payments / max) * 100) : 0;
        const label = `${App.formatDateShort(d.date)} — credit ${App.formatCurrency(
          d.credit
        )}, payments ${App.formatCurrency(d.payments)}`;
        return `<div class="chart-col" title="${App.escapeHtml(label)}">
          <div class="chart-stack">
            <span class="chart-bar credit" style="height:${creditHeight}%"></span>
            <span class="chart-bar payment" style="height:${paymentHeight}%"></span>
          </div>
          <span class="chart-label">${App.formatDateShort(d.date)}</span>
        </div>`;
      })
      .join('')}</div>
      <div class="chart-legend">
        <span><i class="swatch credit"></i>Credit issued</span>
        <span><i class="swatch payment"></i>Payments received</span>
      </div>`;
  }

  function renderTopDebtors(debtors) {
    const body = document.getElementById('debtorsBody');
    const empty = document.getElementById('debtorsEmpty');
    const wrap = document.getElementById('debtorsWrap');
    if (!body) return;

    if (debtors.length === 0) {
      if (wrap) wrap.hidden = true;
      if (empty) {
        empty.hidden = false;
        empty.innerHTML = App.emptyState('🎉', 'Nobody owes you anything.');
      }
      return;
    }

    if (wrap) wrap.hidden = false;
    if (empty) empty.hidden = true;

    body.innerHTML = debtors
      .map(
        (c, i) => `<tr>
          <td>${i + 1}</td>
          <td class="wrap"><a href="customer-profile.html?id=${c.id}">${App.escapeHtml(c.fullName)}</a></td>
          <td>${App.escapeHtml(c.phone || '—')}</td>
          <td>${c.dueDate ? App.formatDate(c.dueDate) : '—'}</td>
          <td>${App.statusBadge(c.status)}</td>
          <td class="num amount-credit">${App.formatCurrency(c.balance)}</td>
        </tr>`
      )
      .join('');
  }

  function renderOverdue(overdue) {
    const body = document.getElementById('overdueBody');
    const empty = document.getElementById('overdueEmpty');
    const wrap = document.getElementById('overdueWrap');
    if (!body) return;

    if (overdue.length === 0) {
      if (wrap) wrap.hidden = true;
      if (empty) {
        empty.hidden = false;
        empty.innerHTML = App.emptyState('✅', 'No overdue accounts.');
      }
      return;
    }

    if (wrap) wrap.hidden = false;
    if (empty) empty.hidden = true;

    body.innerHTML = overdue
      .map(
        (c) => `<tr>
          <td class="wrap"><a href="customer-profile.html?id=${c.id}">${App.escapeHtml(c.fullName)}</a></td>
          <td>${App.escapeHtml(c.phone || '—')}</td>
          <td>${App.formatDate(c.dueDate)}</td>
          <td class="num text-danger">${c.daysOverdue}</td>
          <td class="num amount-credit">${App.formatCurrency(c.balance)}</td>
        </tr>`
      )
      .join('');
  }

  async function load() {
    const periodSelect = document.getElementById('periodSelect');
    const days = periodSelect ? Number(periodSelect.value) : 30;

    try {
      const data = await API.reports.full(days);
      const s = data.summary;

      App.setText('repOutstanding', App.formatCurrency(s.totalOutstanding));
      App.setText('repOverdue', App.formatCurrency(s.totalOverdue));
      App.setText('repCreditIssued', App.formatCurrency(s.totalCreditIssued));
      App.setText('repPayments', App.formatCurrency(s.totalPayments));
      App.setText('repCustomers', String(s.totalCustomers));
      App.setText('repCustomersOwing', String(s.customersOwing));
      App.setText('repCustomersOverdue', String(s.customersOverdue));
      App.setText('repPaidThisMonth', App.formatCurrency(s.paidThisMonth));
      App.setText('repCreditThisMonth', App.formatCurrency(s.creditThisMonth));

      renderTopDebtors(data.topDebtors);
      renderOverdue(data.overdueCustomers);
      renderActivityChart(data.transactionsByDate);
    } catch (err) {
      App.handleError(err);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'reports') return;
    document.getElementById('periodSelect')?.addEventListener('change', load);
    load();
  });
})();
