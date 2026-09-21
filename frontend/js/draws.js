// draws.js — money the owner takes from the shop, this month.
// Uses the same /api/cash endpoint as Transactions, filtered to DRAW.

(() => {
  let entries = [];

  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                  'August', 'September', 'October', 'November', 'December'];

  async function load() {
    const today = App.todayISO();
    const monthStart = `${today.slice(0, 8)}01`;

    try {
      const data = await API.cash.list({ type: 'DRAW', from: monthStart, to: today });
      entries = data.entries;
      App.setText('drawsTotal', App.formatRands(data.totals.draws));

      document.getElementById('drawList').innerHTML = entries.length
        ? entries.map((entry) => CashEntry.rowHtml(entry, 'button')).join('')
        : `<div class="tc-empty"><span class="emoji">👛</span><p>No draws logged this month.</p></div>`;
    } catch (err) {
      App.handleError(err);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'draws') return;

    document.getElementById('backBtn').innerHTML = App.ICONS.back;
    App.setText('monthTitle', `${MONTHS[new Date().getMonth()]} draws`);

    document.getElementById('logDrawBtn').addEventListener('click', () => {
      CashEntry.open({ type: 'DRAW', onSaved: load });
    });

    document.getElementById('drawList').addEventListener('click', (e) => {
      const row = e.target.closest('[data-entry-id]');
      if (!row) return;
      const entry = entries.find((x) => x.id === Number(row.dataset.entryId));
      if (entry) CashEntry.openDetails(entry, load);
    });

    load();
  });
})();
