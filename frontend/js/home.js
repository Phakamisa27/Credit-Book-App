// home.js — the ThathaCash Home screen.
//
// Home leads with ONE number: cash available. Safe to draw sits behind an
// expander with its working shown, draws this month are one quiet line, stock
// is one line, and everything else lives in the menu.
//
// The Safe to draw sum itself is worked out on the server
// (shop_rules.calculate_safe_to_draw); this file only shows it.
//
// Three states:
//   1. No entries yet  -> only the "count your cash" form.
//   2. Just counted    -> the numbers and one action. Nothing else.
//   3. Coming back     -> the same, plus a line if stock is running low.

(() => {
  // True only between saving the first cash count and leaving the page, so
  // step 2 stays a single result rather than a full dashboard.
  let justCounted = false;
  let cashAvailable = 0;
  let recountModal = null;

  function firstName() {
    const user = API.getCachedUser();
    return ((user && user.fullName) || '').trim().split(/\s+/)[0] || '';
  }

  function show(id, visible) {
    document.getElementById(id).hidden = !visible;
  }

  function renderHello(cash) {
    const name = firstName();
    App.setText('greeting', name ? `Sawubona, ${name}` : 'Sawubona');

    let message = 'This is the cash in your shop.';
    if (!cash.hasEntries) message = "Let's start by counting your cash.";
    else if (cash.cashAvailable < 0) {
      message = 'More money went out than came in. Check your entries, or recount.';
    }
    App.setText('helloSub', message);
  }

  // "today, 08:15" / "yesterday, 17:40" / "on 12 Sep, 09:00"
  function whenCounted(isoTimestamp) {
    const d = new Date(isoTimestamp);
    const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    const startOfDay = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const daysAgo = Math.round((startOfDay(new Date()) - startOfDay(d)) / 86400000);

    if (daysAgo === 0) return `today, ${time}`;
    if (daysAgo === 1) return `yesterday, ${time}`;
    // Local date, not toISOString(): that is UTC and can be a day out.
    const localDate = `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
    return `on ${App.formatDateShort(localDate)}, ${time}`;
  }

  function renderCounted(cash) {
    App.setText(
      'countedText',
      cash.cashCountedAt ? `Cash last counted ${whenCounted(cash.cashCountedAt)}` : 'Cash not counted yet'
    );
    App.setText('recountBtn', cash.cashCountedAt ? 'Recount' : 'Count now');
  }

  function restockNote(std) {
    if (std.restockSource === 'AVERAGE') return 'Based on your average daily stock spend';
    if (std.restockReserveSet) return 'Set by you';
    return 'Not set yet';
  }

  function renderSafeToDraw(cash) {
    const std = cash.safeToDraw;
    App.setText('safeToDraw', App.formatRands(std.amount));
    App.setText('bdCash', App.formatRands(cash.cashAvailable));
    App.setText('bdRestock', App.formatRands(std.restockReserve));
    App.setText('bdRestockNote', restockNote(std));
    App.setText('bdBuffer', App.formatRands(std.buffer));
    App.setText('bdBufferNote', `${std.bufferPercent}% of your cash`);
    App.setText('bdSafe', App.formatRands(std.amount));

    // Too little stock history to average, and no amount of their own: ask.
    show('reservePrompt', std.restockSource === 'OWNER' && !std.restockReserveSet);
  }

  function renderDrawn(cash) {
    const count = cash.drawsThisMonthCount;
    App.setText(
      'drawnSub',
      count ? `${count} draw${count === 1 ? '' : 's'}` : 'Nothing drawn yet this month'
    );
    App.setText('drawnTotal', App.formatRands(cash.drawsThisMonth));
    show('drawnTotal', count > 0);
  }

  function renderCash(cash) {
    cashAvailable = cash.cashAvailable;
    App.setText('cashAvailable', App.formatRands(cash.cashAvailable));
    document.getElementById('cashHero').classList.toggle('negative', cash.cashAvailable < 0);
    renderCounted(cash);
    renderSafeToDraw(cash);
    renderDrawn(cash);
  }

  // One line, or nothing at all. Stock itself lives on the Stock tab.
  function renderLowStock(lowCount) {
    const line = document.getElementById('lowStockLine');
    if (justCounted || lowCount === 0) {
      line.hidden = true;
      return;
    }
    App.setText('lowStockText', `${lowCount} item${lowCount === 1 ? '' : 's'} running low`);
    line.hidden = false;
  }

  async function load() {
    try {
      const data = await API.home.get();

      renderHello(data.cash);
      show('setupCard', !data.cash.hasEntries);
      show('cashView', data.cash.hasEntries);

      if (data.cash.hasEntries) {
        renderCash(data.cash);
        renderLowStock(data.stock.lowCount);
      }
    } catch (err) {
      App.handleError(err);
      App.setText('helloSub', err.message);
    }
  }

  function initSetupForm() {
    const form = document.getElementById('setupForm');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const amount = Number(form.elements.startingCash.value);
      if (!Number.isFinite(amount) || amount <= 0) {
        App.toastError('Enter the cash in your shop, e.g. 3000');
        return;
      }
      await App.withBusy(form.querySelector('button'), async () => {
        try {
          await API.cash.create({
            type: 'OPENING',
            amount,
            note: 'Starting cash',
            date: App.todayISO(),
          });
          justCounted = true;
          load();
        } catch (err) {
          App.handleError(err);
        }
      });
    });
  }

  // ------------------------------------------------------------ recount --
  // The owner counts the till; cash available is corrected to match.
  function initRecount() {
    recountModal = Modal.create('recountModal');
    const form = document.getElementById('recountForm');
    const errorEl = document.getElementById('recountError');

    document.getElementById('recountBtn').addEventListener('click', () => {
      form.reset();
      errorEl.hidden = true;
      App.setText('recountHint', `ThathaCash has ${App.formatRands(cashAvailable)} written down.`);
      recountModal.open();
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      const raw = form.elements.countedCash.value.trim();
      // An empty till (R0) is a real count.
      if (!/^\d+(\.\d{1,2})?$/.test(raw)) {
        errorEl.textContent = 'Enter the cash you counted, e.g. 1840 or 1840.50';
        errorEl.hidden = false;
        return;
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const { difference } = await API.cash.count(Number(raw));
          recountModal.close();
          if (difference === 0) App.toastSuccess('Cash confirmed ✓');
          else if (difference > 0) {
            App.toastSuccess(`Cash updated: ${App.formatRands(difference)} more than written down`);
          } else {
            App.toastSuccess(`Cash updated: ${App.formatRands(-difference)} less than written down`);
          }
          justCounted = false;
          load();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'home') return;

    document.getElementById('brand').insertAdjacentHTML('afterbegin', App.LOGO_SVG);
    document.getElementById('lowStockChevron').innerHTML = App.ICONS.chevron;

    // No type: the owner picks Sale / Stock purchase / Personal draw / Other.
    document.getElementById('logMoneyBtn').addEventListener('click', () => {
      CashEntry.open({
        onSaved: () => {
          justCounted = false; // past the first-run result now
          load();
        },
      });
    });

    initSetupForm();
    initRecount();
    load();

    // Cash and settings change on other screens; refresh when the owner comes back.
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) load();
    });
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) load();
    });
  });
})();
