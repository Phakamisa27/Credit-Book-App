// home.js — the ThathaCash Home screen.
//
// Home deliberately shows ONE number: cash available. The 30% rule sits behind
// an expander, stock is one line, and everything else lives in the menu.
//
// Three states:
//   1. No entries yet  -> only the "count your cash" form.
//   2. Just counted    -> the numbers and one action. Nothing else.
//   3. Coming back     -> the same, plus a line if stock is running low.

(() => {
  // True only between saving the first cash count and leaving the page, so
  // step 2 stays a single result rather than a full dashboard.
  let justCounted = false;

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
    else if (justCounted) message = 'Your cash is counted. ✓';
    else if (cash.cashAvailable < 0) {
      message = 'More money went out than came in. Check your entries.';
    }
    App.setText('helloSub', message);
  }

  function renderCash(cash) {
    App.setText('cashAvailable', App.formatRands(cash.cashAvailable));
    App.setText('safeToUse', App.formatRands(cash.availableForStock));
    App.setText('keptForExpenses', App.formatRands(cash.keptForExpenses));
    App.setText(
      'reserveHint',
      `We keep ${cash.reservePercent}% of your cash as a buffer for emergencies. ` +
        'The rest is safe to draw or spend on stock.'
    );
    document.getElementById('cashHero').classList.toggle('negative', cash.cashAvailable < 0);
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

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'home') return;

    document.getElementById('brand').insertAdjacentHTML('afterbegin', App.LOGO_SVG);
    document.getElementById('lowStockChevron').innerHTML = App.ICONS.chevron;

    document.getElementById('logMoneyBtn').addEventListener('click', () => {
      CashEntry.open({
        onSaved: () => {
          justCounted = false; // past the first-run result now
          load();
        },
      });
    });

    initSetupForm();
    load();

    // Cash changes on other screens; refresh when the owner comes back.
    window.addEventListener('pageshow', (e) => {
      if (e.persisted) load();
    });
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) load();
    });
  });
})();
