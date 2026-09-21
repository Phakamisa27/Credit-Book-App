// money.js — the Transactions screen: money in and out for a chosen period.
//
// (The Credit Book's old credit feed lives in transactions.js, which the
// record-credit page still uses.)

(() => {
  let type = ''; // '' = all kinds
  let entries = [];

  const TITLES = {
    '': 'All transactions',
    INCOME: 'Income',
    EXPENSE: 'Expenses',
    STOCK: 'Stock purchases',
    DRAW: 'Draws',
  };

  function iso(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate()
    ).padStart(2, '0')}`;
  }

  // The chosen period as { from, to } dates, both inclusive.
  function periodRange(period) {
    const now = new Date();
    const today = iso(now);

    if (period === 'today') return { from: today, to: today };
    if (period === 'week') {
      const monday = new Date(now);
      monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
      return { from: iso(monday), to: today };
    }
    if (period === 'month') {
      return { from: iso(new Date(now.getFullYear(), now.getMonth(), 1)), to: today };
    }
    if (period === 'lastMonth') {
      return {
        from: iso(new Date(now.getFullYear(), now.getMonth() - 1, 1)),
        to: iso(new Date(now.getFullYear(), now.getMonth(), 0)), // day 0 = last day of previous month
      };
    }
    return { from: '', to: '' }; // all time
  }

  function renderTotals(totals) {
    App.setText('totalIncome', App.formatRands(totals.income));
    App.setText('totalOut', App.formatRands(totals.moneyOut));
    App.setText('totalExpenses', App.formatRands(totals.expenses));
    App.setText('totalStock', App.formatRands(totals.stock));
    App.setText('totalDraws', App.formatRands(totals.draws));
  }

  function renderList() {
    App.setText('listTitle', TITLES[type]);
    const el = document.getElementById('entryList');
    el.innerHTML = entries.length
      ? entries.map((entry) => CashEntry.rowHtml(entry, 'button')).join('')
      : `<div class="tc-empty"><span class="emoji">🧾</span><p>Nothing logged for this period.</p></div>`;
  }

  async function load() {
    const { from, to } = periodRange(document.getElementById('period').value);
    try {
      const data = await API.cash.list({ type, from, to });
      entries = data.entries;
      renderTotals(data.totals);
      renderList();
    } catch (err) {
      App.handleError(err);
      App.setHtml('entryList', `<div class="tc-empty"><p>${App.escapeHtml(err.message)}</p></div>`);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'transactions') return;

    document.querySelectorAll('[data-type]').forEach((chip) => {
      chip.addEventListener('click', () => {
        type = chip.dataset.type;
        document.querySelectorAll('[data-type]').forEach((c) => c.classList.toggle('active', c === chip));
        load();
      });
    });

    document.getElementById('period').addEventListener('change', load);

    // "+ Log money" starts on whichever kind of entry is being viewed.
    document.getElementById('addEntryBtn').addEventListener('click', () => {
      CashEntry.open({ type: type || 'INCOME', onSaved: load });
    });

    document.getElementById('entryList').addEventListener('click', (e) => {
      const row = e.target.closest('[data-entry-id]');
      if (!row) return;
      const entry = entries.find((x) => x.id === Number(row.dataset.entryId));
      if (entry) CashEntry.openDetails(entry, load);
    });

    load();
  });
})();
