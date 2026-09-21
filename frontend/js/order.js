// order.js — the suggested order, and sharing it with the wholesaler on WhatsApp.
//
// The server suggests the order (GET /api/order). The owner can then change
// amounts or remove lines here. Those edits are only a draft in the browser —
// nothing is saved until money is actually paid and logged as a stock purchase.

(() => {
  let lines = []; // [{ id, name, inStock, orderQuantity, unitPrice }]
  let availableForStock = 0;

  // Money in cents, so 3 × R38.50 is exactly R115.50.
  function totalCents() {
    return lines.reduce((sum, l) => sum + l.orderQuantity * Math.round(l.unitPrice * 100), 0);
  }

  function renderTotalAndBudget() {
    const total = totalCents() / 100;
    App.setText('orderTotal', App.formatRands(total));

    const alert = document.getElementById('budgetAlert');
    alert.hidden = lines.length === 0;
    if (total <= availableForStock) {
      alert.className = 'budget-alert ok';
      alert.textContent = `✓ Fits in your stock budget of ${App.formatRands(availableForStock)}.`;
    } else {
      alert.className = 'budget-alert warn';
      alert.textContent =
        `⚠ This is ${App.formatRands(total - availableForStock)} more than you can safely ` +
        `spend on stock (${App.formatRands(availableForStock)}). Remove or reduce some items.`;
    }
  }

  function render() {
    const el = document.getElementById('orderLines');
    document.getElementById('orderActions').hidden = lines.length === 0;

    if (lines.length === 0) {
      el.innerHTML = `<div class="tc-empty">
        <span class="emoji">🎉</span>
        <p>Nothing to order. None of your products are running low.</p>
        <a class="btn btn-outline" href="stock.html">Check your stock</a>
      </div>`;
      renderTotalAndBudget();
      return;
    }

    el.innerHTML = lines
      .map(
        (l) => `<div class="tc-row" data-id="${l.id}">
          <span class="tc-row-icon" aria-hidden="true">${App.itemEmoji(l.name)}</span>
          <span class="tc-row-main">
            <span class="tc-row-title">${App.escapeHtml(l.name)}</span>
            <span class="tc-row-sub">${App.unitsText(l.inStock)} left · ${App.formatRands(l.unitPrice)} each</span>
            <span class="order-line-controls stepper sm">
              <button type="button" data-step="-1" aria-label="Order one less ${App.escapeHtml(l.name)}">−</button>
              <output>${l.orderQuantity}</output>
              <button type="button" data-step="1" aria-label="Order one more ${App.escapeHtml(l.name)}">+</button>
            </span>
          </span>
          <span class="order-line-total">${App.formatRands((l.orderQuantity * Math.round(l.unitPrice * 100)) / 100)}</span>
          <button type="button" class="remove-btn" data-remove aria-label="Remove ${App.escapeHtml(l.name)}">×</button>
        </div>`
      )
      .join('');

    renderTotalAndBudget();
  }

  // --------------------------------------------------------- WhatsApp ----
  function orderMessage() {
    const user = API.getCachedUser() || {};
    const shop = user.businessName || user.fullName || 'my shop';
    const phone = user.businessPhone ? ` (${user.businessPhone})` : '';

    const items = lines.map((l) => `• ${l.name} × ${l.orderQuantity}`).join('\n');
    return `Hi 👋 I'd like to place an order:\n\n${items}\n\nFrom: ${shop}${phone}\nThank you!`;
  }

  function sendOnWhatsApp() {
    // No number in the link: WhatsApp asks which contact to send it to, so
    // the owner picks their own wholesaler.
    const url = `https://wa.me/?text=${encodeURIComponent(orderMessage())}`;
    window.open(url, '_blank', 'noopener');
  }

  // ------------------------------------------------------------- load ----
  async function load() {
    try {
      const order = await API.order.get();
      availableForStock = order.availableForStock;
      lines = order.items.map((item) => ({
        id: item.id,
        name: item.name,
        inStock: item.inStock,
        orderQuantity: item.orderQuantity,
        unitPrice: item.unitPrice,
      }));
      render();
    } catch (err) {
      App.handleError(err);
      App.setHtml('orderLines', `<div class="tc-empty"><p>${App.escapeHtml(err.message)}</p></div>`);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'order') return;

    document.getElementById('backBtn').innerHTML = App.ICONS.back;
    document.getElementById('sendBtn').innerHTML = `${App.ICONS.share} Send order to wholesaler`;

    document.getElementById('orderLines').addEventListener('click', (e) => {
      const row = e.target.closest('[data-id]');
      if (!row) return;
      const line = lines.find((l) => l.id === Number(row.dataset.id));

      if (e.target.closest('[data-remove]')) {
        lines = lines.filter((l) => l !== line);
      } else if (e.target.closest('[data-step]')) {
        const step = Number(e.target.closest('[data-step]').dataset.step);
        line.orderQuantity = Math.max(1, line.orderQuantity + step);
      } else {
        return;
      }
      render();
    });

    document.getElementById('sendBtn').addEventListener('click', sendOnWhatsApp);
    document.getElementById('logPurchaseBtn').addEventListener('click', () => {
      CashEntry.open({
        type: 'STOCK',
        amount: totalCents() / 100,
        note: 'Wholesaler order',
        onSaved: () => {
          window.location.href = 'dashboard.html';
        },
      });
    });

    load();
  });
})();
