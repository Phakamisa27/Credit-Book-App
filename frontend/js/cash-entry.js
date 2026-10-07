// cash-entry.js — the "log money" form, shared by Home, Transactions and Draws.
//
// Usage:
//   CashEntry.open({ onSaved: (entry) => reload() });   // asks what kind first
//   CashEntry.open({ type: 'DRAW', onSaved: reload });   // straight to the form
//   CashEntry.open({ type: 'STOCK', amount: 2700, note: 'Wholesaler order' });
//
// The form is injected into the page the first time it is opened, so no HTML
// file has to carry a copy of it.

const CashEntry = (() => {
  // Everything the owner sees about each kind of entry lives here.
  // `notes` are one-tap suggestions so most entries need no typing.
  const TYPES = {
    INCOME: {
      label: 'Sale',
      title: 'Log a sale',
      choice: 'Money in',
      icon: '💵',
      moneyIn: true,
      hint: 'Money in from selling to customers.',
      noteLabel: 'What for?',
      notes: ['Customer sales', 'Airtime sales', 'Other income'],
    },
    STOCK: {
      label: 'Stock purchase',
      title: 'Log a stock purchase',
      choice: 'Money out · counts towards restocking',
      icon: '🛒',
      moneyIn: false,
      hint: 'Money paid to your wholesaler for stock.',
      noteLabel: 'What for?',
      notes: ['Wholesaler', 'Cash & carry'],
    },
    DRAW: {
      label: 'Personal draw',
      title: 'Log a personal draw',
      choice: 'Money out for you or your family',
      icon: '👛',
      moneyIn: false,
      hint: 'Money you take from the shop for yourself.',
      noteLabel: 'Short reason',
      notes: ['Groceries', 'Transport', 'School fees', 'Grass cutting'],
    },
    EXPENSE: {
      label: 'Shop expense',
      title: 'Log a shop expense',
      choice: 'Electricity, rent, transport…',
      icon: '🧾',
      moneyIn: false,
      hint: 'Money the shop spends that is not stock.',
      noteLabel: 'What for?',
      notes: ['Electricity', 'Rent', 'Transport', 'Airtime', 'Wages'],
    },
    // Not in the choice: only asked for once, when the owner starts.
    OPENING: {
      label: 'Starting cash',
      title: 'Your starting cash',
      icon: '🏦',
      moneyIn: true,
      hint: 'The cash that was already in the shop when you started using ThathaCash.',
      notes: [],
    },
    // Written by "Recount" on Home, never logged here. Listed so they show
    // properly on Transactions.
    RECOUNT_IN: { label: 'Cash recount', icon: '🔢', moneyIn: true, notes: [] },
    RECOUNT_OUT: { label: 'Cash recount', icon: '🔢', moneyIn: false, notes: [] },
  };

  // The four kinds the owner picks between, in the order they happen most.
  const CHOICES = [
    { type: 'INCOME', name: 'Sale' },
    { type: 'STOCK', name: 'Stock purchase' },
    { type: 'DRAW', name: 'Personal draw' },
    { type: 'EXPENSE', name: 'Other shop expense' },
  ];

  let modal = null;
  let form = null;
  let current = { type: 'INCOME', onSaved: null, chose: false };

  // --------------------------------------------------------------- markup --
  function inject() {
    const choiceButtons = CHOICES.map(
      ({ type, name }) => `<button type="button" class="tc-row" data-choose="${type}">
          <span class="tc-row-icon ${TYPES[type].moneyIn ? 'in' : 'out'}" aria-hidden="true">
            ${TYPES[type].icon}
          </span>
          <span class="tc-row-main">
            <span class="tc-row-title">${name}</span>
            <span class="tc-row-sub">${TYPES[type].choice}</span>
          </span>
          <span class="tc-chevron">${App.ICONS.chevron}</span>
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
            <div class="choice-list" data-step="choose" role="group" aria-label="What kind of money?">
              ${choiceButtons}
            </div>

            <form id="cashEntryForm" data-step="form" novalidate>
              <button type="button" class="link-btn change-type" data-change-type>← Change type</button>
              <p class="form-error" data-error hidden></p>

              <div class="form-group">
                <label for="cashEntryAmount">Amount (R)</label>
                <input class="form-control amount-input" id="cashEntryAmount" type="number"
                  inputmode="decimal" min="0.01" step="0.01" placeholder="0" required />
                <p class="form-hint" data-hint></p>
              </div>

              <div class="form-group" data-note-group>
                <label for="cashEntryNote"><span data-note-label>What for?</span>
                  <span class="muted">(optional)</span></label>
                <input class="form-control" id="cashEntryNote" type="text" maxlength="200" />
                <div class="note-chips" data-note-chips></div>
              </div>

              <div class="form-group">
                <label for="cashEntryDate">Date</label>
                <input class="form-control" id="cashEntryDate" type="date" required />
              </div>

              <!-- A soft warning only. The owner can always go ahead. -->
              <div class="draw-warning" data-warning role="alert" hidden>
                <p data-warning-text></p>
                <p class="draw-warning-sub" data-warning-sub></p>
                <div class="modal-actions">
                  <button class="btn btn-outline" type="button" data-warning-cancel>Cancel</button>
                  <button class="btn btn-primary" type="button" data-warning-continue>Continue</button>
                </div>
              </div>

              <button class="btn btn-primary" type="submit" data-save>Save</button>
            </form>
          </div>
        </div>
      </div>`
    );

    modal = Modal.create('cashEntryModal');
    form = document.getElementById('cashEntryForm');

    modal.el.querySelectorAll('[data-choose]').forEach((btn) => {
      btn.addEventListener('click', () => {
        current.chose = true;
        showForm(btn.dataset.choose);
      });
    });
    form.querySelector('[data-change-type]').addEventListener('click', showChoice);

    form.querySelector('[data-note-chips]').addEventListener('click', (e) => {
      const chip = e.target.closest('button');
      if (!chip) return;
      document.getElementById('cashEntryNote').value = chip.textContent;
    });

    form.querySelector('[data-warning-cancel]').addEventListener('click', hideWarning);
    form.querySelector('[data-warning-continue]').addEventListener('click', submit);

    // Changing the amount after a warning means the warning no longer fits.
    document.getElementById('cashEntryAmount').addEventListener('input', hideWarning);

    form.addEventListener('submit', save);
  }

  // ---------------------------------------------------------------- steps --
  function showChoice() {
    document.getElementById('cashEntryTitle').textContent = 'Log money';
    modal.el.querySelector('[data-step="choose"]').hidden = false;
    form.hidden = true;
    modal.el.querySelector('[data-choose]').focus();
  }

  function showForm(type) {
    current.type = type;
    const config = TYPES[type];

    modal.el.querySelector('[data-step="choose"]').hidden = true;
    form.hidden = false;
    // "Change type" only makes sense if the owner picked the type themselves.
    form.querySelector('[data-change-type]').hidden = !current.chose;
    hideWarning();

    document.getElementById('cashEntryTitle').textContent = config.title;
    form.querySelector('[data-hint]').textContent = config.hint;

    form.querySelector('[data-note-group]').hidden = config.notes.length === 0;
    form.querySelector('[data-note-label]').textContent = config.noteLabel || 'What for?';
    form.querySelector('[data-note-chips]').innerHTML = config.notes
      .map((note) => `<button type="button">${App.escapeHtml(note)}</button>`)
      .join('');

    document.getElementById('cashEntryAmount').focus();
  }

  function hideWarning() {
    if (!form) return;
    form.querySelector('[data-warning]').hidden = true;
    form.querySelector('[data-save]').hidden = false;
  }

  function showWarning(text, sub) {
    form.querySelector('[data-warning-text]').textContent = text;
    form.querySelector('[data-warning-sub]').textContent = sub;
    form.querySelector('[data-warning]').hidden = false;
    form.querySelector('[data-save]').hidden = true;
    form.querySelector('[data-warning-continue]').focus();
  }

  // ----------------------------------------------------------------- open --
  // Without a `type` the owner is asked what kind of money it is first.
  function open({ type = null, amount = '', note = '', onSaved = null } = {}) {
    if (!modal) inject();

    current = { type, onSaved, chose: false };
    form.reset();
    form.querySelector('[data-error]').hidden = true;
    document.getElementById('cashEntryAmount').value = amount;
    document.getElementById('cashEntryNote').value = note;
    document.getElementById('cashEntryDate').value = App.todayISO();

    modal.open();
    if (type && TYPES[type]) showForm(type);
    else showChoice();
  }

  // ----------------------------------------------------------------- save --
  function fail(message) {
    const errorEl = form.querySelector('[data-error]');
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  // The form's values, or null (after showing why) if they are not usable.
  function readForm() {
    const raw = document.getElementById('cashEntryAmount').value.trim();
    const amount = Number(raw);
    if (!raw || !Number.isFinite(amount) || amount <= 0) {
      fail('Enter an amount bigger than R0.');
      return null;
    }
    // Checked on the text, not the number: 0.29 * 100 is 28.999… in floating point.
    if (!/^\d+(\.\d{1,2})?$/.test(raw)) {
      fail('Use at most two decimals, e.g. 25.50');
      return null;
    }
    return {
      type: current.type,
      amount,
      note: document.getElementById('cashEntryNote').value.trim(),
      date: document.getElementById('cashEntryDate').value || App.todayISO(),
    };
  }

  // A draw bigger than Safe to draw gets a warning first — never a block.
  // Returns true if the warning is now showing.
  async function warnAboutDraw(data) {
    if (data.type !== 'DRAW') return false;
    let cash = null;
    try {
      cash = await API.cash.summary();
    } catch (_) {
      return false; // Could not check. Saving will say what is wrong, if anything is.
    }
    if (data.amount <= cash.safeToDraw.amount) return false;

    const left = Math.max(0, cash.cashAvailable - data.amount);
    showWarning(
      `This leaves ${App.formatRands(left)} for restocking. Continue?`,
      `Safe to draw right now is ${App.formatRands(cash.safeToDraw.amount)}.`
    );
    return true;
  }

  async function create(data) {
    try {
      const entry = await API.cash.create(data);
      modal.close();
      App.toastSuccess(`${TYPES[entry.type].label} of ${App.formatRands(entry.amount)} saved`);
      if (current.onSaved) current.onSaved(entry);
    } catch (err) {
      fail(err.message);
    }
  }

  // The button stays busy for the check AND the save, so a double tap can
  // never log the same money twice.
  async function save(e) {
    e.preventDefault();
    form.querySelector('[data-error]').hidden = true;
    const data = readForm();
    if (!data) return;

    await App.withBusy(form.querySelector('[data-save]'), async () => {
      if (await warnAboutDraw(data)) return;
      await create(data);
    });
  }

  // "Continue" after the warning: the owner has decided, so no second check.
  async function submit() {
    form.querySelector('[data-error]').hidden = true;
    const data = readForm();
    if (!data) return;

    await App.withBusy(form.querySelector('[data-warning-continue]'), () => create(data));
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
