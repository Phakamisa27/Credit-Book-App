// cash-entry.js — the "log money" form, shared by Home, Transactions and Draws.
//
// Usage:
//   CashEntry.open({ type: 'DRAW', onSaved: (entry) => reload() });
//   CashEntry.open({ type: 'STOCK', amount: 2700, note: 'Wholesaler order' });
//
// The form is injected into the page the first time it is opened, so no HTML
// file has to carry a copy of it.

const CashEntry = (() => {
  // Everything the owner sees about each kind of entry lives here.
  // `notes` are one-tap suggestions so most entries need no typing.
  const TYPES = {
    INCOME: {
      label: 'Money in',
      title: 'Log money in',
      icon: '💵',
      moneyIn: true,
      hint: 'Sales and any other money coming into the shop.',
      notes: ['Customer sales', 'Airtime sales', 'Other income'],
    },
    EXPENSE: {
      label: 'Expense',
      title: 'Log an expense',
      icon: '🧾',
      moneyIn: false,
      hint: 'Money the shop spends that is not stock.',
      notes: ['Electricity', 'Rent', 'Transport', 'Airtime', 'Wages'],
    },
    STOCK: {
      label: 'Stock',
      title: 'Log a stock purchase',
      icon: '🛒',
      moneyIn: false,
      hint: 'Money paid to your wholesaler for stock.',
      notes: ['Wholesaler', 'Cash & carry'],
    },
    DRAW: {
      label: 'Draw',
      title: 'Log a draw',
      icon: '👛',
      moneyIn: false,
      hint: 'Money you take from the shop for yourself or your family.',
      notes: ['Personal', 'Family', 'Transport', 'School fees'],
    },
    // Not in the picker: only asked for once, when the owner starts.
    OPENING: {
      label: 'Starting cash',
      title: 'Your starting cash',
      icon: '🏦',
      moneyIn: true,
      hint: 'The cash that was already in the shop when you started using ThathaCash.',
      notes: [],
    },
  };

  const PICKER_TYPES = ['INCOME', 'EXPENSE', 'STOCK', 'DRAW'];

  let modal = null;
  let form = null;
  let current = { type: 'INCOME', onSaved: null };

  // --------------------------------------------------------------- markup --
  function inject() {
    const pickerButtons = PICKER_TYPES.map(
      (type) => `<button type="button" data-type="${type}" aria-pressed="false">
          <span aria-hidden="true">${TYPES[type].icon}</span>${TYPES[type].label}
        </button>`
    ).join('');

    document.body.insertAdjacentHTML(
      'beforeend',
      `<div class="modal" id="cashEntryModal" hidden>
        <div class="modal-backdrop" data-close></div>
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="cashEntryTitle">
          <div class="modal-head">
            <h3 id="cashEntryTitle">Log money</h3>
            <button type="button" class="modal-close" data-close aria-label="Close">×</button>
          </div>
          <div class="modal-body">
            <form id="cashEntryForm" novalidate>
              <p class="form-error" data-error hidden></p>

              <div class="type-picker" role="group" aria-label="What kind of money?">
                ${pickerButtons}
              </div>

              <div class="form-group">
                <label for="cashEntryAmount">Amount (R)</label>
                <input class="form-control amount-input" id="cashEntryAmount" type="number"
                  inputmode="decimal" min="0.01" step="0.01" placeholder="0" required />
                <p class="form-hint" data-hint></p>
              </div>

              <div class="form-group" data-note-group>
                <label for="cashEntryNote">What for? <span class="muted">(optional)</span></label>
                <input class="form-control" id="cashEntryNote" type="text" maxlength="200" />
                <div class="note-chips" data-note-chips></div>
              </div>

              <div class="form-group">
                <label for="cashEntryDate">Date</label>
                <input class="form-control" id="cashEntryDate" type="date" required />
              </div>

              <button class="btn btn-primary" type="submit">Save</button>
            </form>
          </div>
        </div>
      </div>`
    );

    modal = Modal.create('cashEntryModal');
    form = document.getElementById('cashEntryForm');

    form.querySelectorAll('[data-type]').forEach((btn) => {
      btn.addEventListener('click', () => setType(btn.dataset.type));
    });

    form.querySelector('[data-note-chips]').addEventListener('click', (e) => {
      const chip = e.target.closest('button');
      if (!chip) return;
      document.getElementById('cashEntryNote').value = chip.textContent;
    });

    form.addEventListener('submit', save);
  }

  function setType(type) {
    current.type = type;
    const config = TYPES[type];

    document.getElementById('cashEntryTitle').textContent = config.title;
    form.querySelector('[data-hint]').textContent = config.hint;

    // Starting cash is a one-off, so there is nothing to pick between.
    form.querySelector('.type-picker').hidden = type === 'OPENING';
    form.querySelectorAll('[data-type]').forEach((btn) => {
      btn.setAttribute('aria-pressed', String(btn.dataset.type === type));
    });

    form.querySelector('[data-note-group]').hidden = config.notes.length === 0;
    form.querySelector('[data-note-chips]').innerHTML = config.notes
      .map((note) => `<button type="button">${App.escapeHtml(note)}</button>`)
      .join('');
  }

  // ----------------------------------------------------------------- open --
  function open({ type = 'INCOME', amount = '', note = '', onSaved = null } = {}) {
    if (!modal) inject();

    current = { type, onSaved };
    form.reset();
    form.querySelector('[data-error]').hidden = true;
    document.getElementById('cashEntryAmount').value = amount;
    document.getElementById('cashEntryNote').value = note;
    document.getElementById('cashEntryDate').value = App.todayISO();
    setType(type);

    modal.open();
  }

  // ----------------------------------------------------------------- save --
  async function save(e) {
    e.preventDefault();
    const errorEl = form.querySelector('[data-error]');
    errorEl.hidden = true;

    const fail = (message) => {
      errorEl.textContent = message;
      errorEl.hidden = false;
    };

    const raw = document.getElementById('cashEntryAmount').value.trim();
    const amount = Number(raw);
    if (!raw || !Number.isFinite(amount) || amount <= 0) {
      return fail('Enter an amount bigger than R0.');
    }
    // Checked on the text, not the number: 0.29 * 100 is 28.999… in floating point.
    if (!/^\d+(\.\d{1,2})?$/.test(raw)) return fail('Use at most two decimals, e.g. 25.50');

    const data = {
      type: current.type,
      amount,
      note: document.getElementById('cashEntryNote').value.trim(),
      date: document.getElementById('cashEntryDate').value || App.todayISO(),
    };

    await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
      try {
        const entry = await API.cash.create(data);
        modal.close();
        App.toastSuccess(`${TYPES[entry.type].label} of ${App.formatRands(entry.amount)} saved`);
        if (current.onSaved) current.onSaved(entry);
      } catch (err) {
        fail(err.message);
      }
    });
  }

  // ------------------------------------------------------------ list rows --
  // "Today", "Yesterday", else "15 Sep 2026".
  function friendlyDate(iso) {
    const today = App.todayISO();
    if (iso === today) return 'Today';
    const d = new Date();
    d.setDate(d.getDate() - 1);
    const yesterday = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate()
    ).padStart(2, '0')}`;
    if (iso === yesterday) return 'Yesterday';
    return App.formatDate(iso);
  }

  // One entry as a list row. `tag` is 'a' (goes to Transactions) or 'button'
  // (the page handles the click, e.g. to offer delete).
  function rowHtml(entry, tag = 'button') {
    const config = TYPES[entry.type] || TYPES.INCOME;
    const direction = config.moneyIn ? 'in' : 'out';
    const title = entry.note || config.label;
    const sub = entry.note ? `${config.label} · ${friendlyDate(entry.date)}` : friendlyDate(entry.date);
    const attrs =
      tag === 'a' ? 'href="transactions.html"' : `type="button" data-entry-id="${entry.id}"`;

    return `<${tag} class="tc-row" ${attrs}>
      <span class="tc-row-icon ${direction}" aria-hidden="true">${config.icon}</span>
      <span class="tc-row-main">
        <span class="tc-row-title">${App.escapeHtml(title)}</span>
        <span class="tc-row-sub">${App.escapeHtml(sub)}</span>
      </span>
      <span class="tc-row-amount ${direction}">
        ${config.moneyIn ? '+' : '−'}${App.formatRands(entry.amount)}
      </span>
    </${tag}>`;
  }

  // ------------------------------------------------------ entry details --
  // Tapping an entry shows it, with a way to delete a mistake. Two taps to
  // delete rather than a browser confirm() pop-up.
  let detailsModal = null;
  let detailsEntry = null;
  let onDeleted = null;

  function injectDetails() {
    document.body.insertAdjacentHTML(
      'beforeend',
      `<div class="modal" id="entryDetailsModal" hidden>
        <div class="modal-backdrop" data-close></div>
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="entryDetailsTitle">
          <div class="modal-head">
            <h3 id="entryDetailsTitle">Entry</h3>
            <button type="button" class="modal-close" data-close aria-label="Close">×</button>
          </div>
          <div class="modal-body">
            <div class="cash-hero-amount" data-amount></div>
            <p class="muted" data-meta></p>
            <p class="form-error" data-error hidden></p>
            <div class="modal-actions">
              <button class="btn btn-outline" type="button" data-close>Close</button>
              <button class="btn btn-outline" type="button" data-delete>Delete</button>
            </div>
          </div>
        </div>
      </div>`
    );
    detailsModal = Modal.create('entryDetailsModal');
    detailsModal.el.querySelector('[data-delete]').addEventListener('click', removeEntry);
  }

  function openDetails(entry, deletedCallback) {
    if (!detailsModal) injectDetails();
    detailsEntry = entry;
    onDeleted = deletedCallback;

    const config = TYPES[entry.type] || TYPES.INCOME;
    const el = detailsModal.el;
    el.querySelector('#entryDetailsTitle').textContent = `${config.icon} ${config.label}`;
    const amount = el.querySelector('[data-amount]');
    amount.textContent = `${config.moneyIn ? '+' : '−'}${App.formatRands(entry.amount)}`;
    amount.style.color = config.moneyIn ? 'var(--green)' : 'var(--red)';
    el.querySelector('[data-meta]').textContent = [entry.note, App.formatDate(entry.date)]
      .filter(Boolean)
      .join(' · ');
    el.querySelector('[data-error]').hidden = true;

    const del = el.querySelector('[data-delete]');
    del.textContent = 'Delete';
    del.className = 'btn btn-outline';
    delete del.dataset.armed;

    detailsModal.open();
  }

  async function removeEntry() {
    const del = detailsModal.el.querySelector('[data-delete]');
    if (!del.dataset.armed) {
      del.dataset.armed = 'yes';
      del.textContent = 'Tap again to delete';
      del.className = 'btn btn-danger';
      return;
    }
    try {
      await API.cash.remove(detailsEntry.id);
      detailsModal.close();
      App.toastSuccess('Entry deleted');
      if (onDeleted) onDeleted();
    } catch (err) {
      const errorEl = detailsModal.el.querySelector('[data-error]');
      errorEl.textContent = err.message;
      errorEl.hidden = false;
    }
  }

  return { TYPES, open, openDetails, rowHtml, friendlyDate };
})();
