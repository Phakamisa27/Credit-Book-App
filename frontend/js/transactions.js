// transactions.js — the record-credit form (multi-item) and the business feed.

(() => {
  // ===================================================== item row editor ==
  //
  // A credit can cover several products bought in one visit. Each row is
  // item + quantity + unit price; the row total and the grand total are
  // recalculated on every keystroke.
  //
  // These figures are a live preview only. The server recomputes the grand
  // total from the same lines when it saves, and its answer is the one that
  // reaches the books.
  function createItemEditor() {
    const rowsEl = document.getElementById('itemRows');
    if (!rowsEl) return null;

    // Money maths in cents — 0.1 + 0.2 must not become 0.30000000000000004.
    function lineTotalOf(row) {
      const quantity = parseInt(row.querySelector('[data-field="quantity"]').value, 10);
      const unitPrice = parseFloat(row.querySelector('[data-field="unitPrice"]').value);
      if (!Number.isInteger(quantity) || quantity < 1) return 0;
      if (!Number.isFinite(unitPrice) || unitPrice <= 0) return 0;
      return (quantity * Math.round(unitPrice * 100)) / 100;
    }

    function recalculate() {
      let grandCents = 0;

      rowsEl.querySelectorAll('[data-row]').forEach((row) => {
        const total = lineTotalOf(row);
        row.querySelector('[data-field="lineTotal"]').textContent = App.formatCurrency(total);
        grandCents += Math.round(total * 100);
      });

      App.setText('grandTotal', App.formatCurrency(grandCents / 100));

      // Only offer removal while more than one row exists — a credit always
      // needs at least one line.
      const rows = rowsEl.querySelectorAll('[data-row]');
      rows.forEach((row) => {
        row.querySelector('[data-remove]').disabled = rows.length === 1;
      });
    }

    function addRow({ name = '', quantity = 1, unitPrice = '' } = {}) {
      const row = document.createElement('div');
      row.className = 'item-row';
      row.setAttribute('data-row', '');
      row.innerHTML = `
        <div class="item-field">
          <label>Item</label>
          <input class="form-control" data-field="name" type="text"
            list="quickItemNames" placeholder="e.g. Bread" />
        </div>
        <div class="item-field">
          <label>Qty</label>
          <input class="form-control" data-field="quantity" type="number"
            min="1" step="1" inputmode="numeric" />
        </div>
        <div class="item-field">
          <label>Unit Price (R)</label>
          <input class="form-control" data-field="unitPrice" type="number"
            min="0.01" step="0.01" inputmode="decimal" placeholder="0.00" />
        </div>
        <div class="item-field item-total-field">
          <label>Total</label>
          <span class="item-total" data-field="lineTotal">R0.00</span>
        </div>
        <div class="item-field item-remove-field">
          <button type="button" class="row-remove" data-remove
            aria-label="Remove this item">×</button>
        </div>`;

      row.querySelector('[data-field="name"]').value = name;
      row.querySelector('[data-field="quantity"]').value = quantity;
      row.querySelector('[data-field="unitPrice"]').value = unitPrice;

      rowsEl.appendChild(row);
      recalculate();
      return row;
    }

    // One listener on the container covers every present and future row.
    rowsEl.addEventListener('input', recalculate);

    rowsEl.addEventListener('click', (e) => {
      const remove = e.target.closest('[data-remove]');
      if (!remove) return;
      if (rowsEl.querySelectorAll('[data-row]').length === 1) return;
      remove.closest('[data-row]').remove();
      recalculate();
    });

    // Reads the rows for submission. Fully blank rows are dropped so a row the
    // owner added and never filled in does not block saving.
    function collect() {
      const items = [];
      const problems = [];

      rowsEl.querySelectorAll('[data-row]').forEach((row, index) => {
        const name = row.querySelector('[data-field="name"]').value.trim();
        const quantityRaw = row.querySelector('[data-field="quantity"]').value.trim();
        const priceRaw = row.querySelector('[data-field="unitPrice"]').value.trim();

        if (!name && !priceRaw && (quantityRaw === '' || quantityRaw === '1')) return;

        const label = `Item ${index + 1}`;
        const quantity = parseInt(quantityRaw, 10);
        const unitPrice = parseFloat(priceRaw);

        if (!name) {
          problems.push(`${label}: enter an item name.`);
          return;
        }
        if (!Number.isInteger(quantity) || quantity < 1) {
          problems.push(`${label} (${name}): quantity must be a whole number of at least 1.`);
          return;
        }
        if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
          problems.push(`${label} (${name}): enter a unit price greater than zero.`);
          return;
        }

        items.push({ name, quantity, unitPrice });
      });

      if (problems.length === 0 && items.length === 0) {
        problems.push('Add at least one item.');
      }

      return { items, problems };
    }

    function grandTotal() {
      let cents = 0;
      rowsEl.querySelectorAll('[data-row]').forEach((row) => {
        cents += Math.round(lineTotalOf(row) * 100);
      });
      return cents / 100;
    }

    document.getElementById('addItemRowBtn')?.addEventListener('click', () => {
      const row = addRow();
      row.querySelector('[data-field="name"]').focus();
    });

    // Start with one empty row so the form is usable immediately.
    addRow();

    return { addRow, collect, recalculate, grandTotal };
  }

  // Owner-defined quick items. Tapping one appends a prefilled row.
  function initQuickItems(editor) {
    const container = document.getElementById('quickItems');
    if (!container) return;

    const datalist = document.getElementById('quickItemNames');
    let items = [];
    let managing = false;

    function render() {
      container.classList.toggle('managing', managing);

      const chips = items
        .map(
          (item) => `<span class="qi-chip">
            <button type="button" class="pill clear qi-fill"
              data-name="${App.escapeHtml(item.name)}" data-price="${item.price}">
              ${App.escapeHtml(item.name)} · ${App.formatCurrency(item.price)}
            </button>
            <button type="button" class="qi-del" data-id="${item.id}"
              aria-label="Delete ${App.escapeHtml(item.name)}">×</button>
          </span>`
        )
        .join('');

      container.innerHTML =
        chips + '<button type="button" class="pill add-item" id="addItemBtn">＋ Add Item</button>';

      if (datalist) {
        datalist.innerHTML = items
          .map((i) => `<option value="${App.escapeHtml(i.name)}"></option>`)
          .join('');
      }
    }

    async function load() {
      try {
        items = await API.items.list();
        render();
      } catch (err) {
        App.handleError(err);
      }
    }

    container.addEventListener('click', async (e) => {
      const fill = e.target.closest('.qi-fill');
      if (fill && !managing) {
        editor.addRow({ name: fill.dataset.name, quantity: 1, unitPrice: fill.dataset.price });
        return;
      }

      const del = e.target.closest('.qi-del');
      if (del) {
        try {
          await API.items.remove(del.dataset.id);
          items = items.filter((i) => String(i.id) !== String(del.dataset.id));
          render();
          App.toastSuccess('Item removed');
        } catch (err) {
          App.handleError(err);
        }
        return;
      }

      if (e.target.closest('#addItemBtn')) {
        const name = prompt('Item name (e.g. Perfume):', '');
        if (name === null) return;
        if (!name.trim()) return App.toastError('Enter an item name');

        const priceInput = prompt(`Price for "${name.trim()}" (R):`, '');
        if (priceInput === null) return;
        const price = parseFloat(priceInput);
        if (!price || price <= 0) return App.toastError('Enter a valid price');

        try {
          const item = await API.items.create({ name: name.trim(), price });
          items.push(item);
          items.sort((a, b) => a.name.localeCompare(b.name));
          render();
          App.toastSuccess('Item added');
        } catch (err) {
          App.handleError(err);
        }
      }
    });

    document.getElementById('manageItemsBtn')?.addEventListener('click', (e) => {
      managing = !managing;
      e.target.textContent = managing ? 'Done' : 'Edit';
      render();
    });

    load();
  }

  // Product photo. Returns a getter for the current base64 data URI.
  function initProductPhoto() {
    const input = document.getElementById('productPhotoInput');
    if (!input) return () => '';

    const empty = document.getElementById('productPhotoEmpty');
    const preview = document.getElementById('productPhotoPreview');
    const previewImg = document.getElementById('productPhotoPreviewImg');
    let photo = '';

    function show(dataUri) {
      photo = dataUri;
      if (previewImg) previewImg.src = dataUri;
      if (preview) preview.hidden = false;
      if (empty) empty.hidden = true;
    }

    function clear() {
      photo = '';
      input.value = '';
      if (previewImg) previewImg.removeAttribute('src');
      if (preview) preview.hidden = true;
      if (empty) empty.hidden = false;
    }

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        App.toastError('Please choose an image file');
        input.value = '';
        return;
      }
      // Keep uploads well under the server's 8mb body limit.
      if (file.size > 3 * 1024 * 1024) {
        App.toastError('That photo is too large. Please use one under 3MB.');
        input.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = () => show(reader.result);
      reader.onerror = () => App.toastError('Could not read that image');
      reader.readAsDataURL(file);
    });

    document.getElementById('productPhotoTrigger')?.addEventListener('click', () => input.click());
    document.getElementById('changePhotoBtn')?.addEventListener('click', () => input.click());
    document.getElementById('removePhotoBtn')?.addEventListener('click', clear);

    return () => photo;
  }

  // Signature pad. Returns a getter for the saved signature.
  function initSignaturePad() {
    const canvas = document.getElementById('signatureCanvas');
    const wrap = document.getElementById('signatureWrap');
    if (!canvas || !wrap) return () => '';

    const ctx = canvas.getContext('2d');
    let saved = '';
    let drawing = false;
    let hasStroke = false;
    let lastX = 0;
    let lastY = 0;

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      // Preserve whatever is on the canvas across a resize.
      const existing = saved || (hasStroke ? canvas.toDataURL('image/png') : null);

      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      ctx.strokeStyle = '#1a2e24';
      ctx.lineWidth = 2.2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (existing) {
        const img = new Image();
        img.onload = () => ctx.drawImage(img, 0, 0, rect.width, rect.height);
        img.src = existing;
      }
    }

    function pos(e) {
      const rect = canvas.getBoundingClientRect();
      const source = e.touches ? e.touches[0] : e;
      return { x: source.clientX - rect.left, y: source.clientY - rect.top };
    }

    function start(e) {
      if (e.cancelable) e.preventDefault();
      drawing = true;
      const p = pos(e);
      lastX = p.x;
      lastY = p.y;
    }

    function draw(e) {
      if (!drawing) return;
      if (e.cancelable) e.preventDefault();
      const p = pos(e);
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();
      lastX = p.x;
      lastY = p.y;
      if (!hasStroke) {
        hasStroke = true;
        wrap.classList.add('has-stroke');
      }
    }

    function stop(e) {
      if (e && e.cancelable) e.preventDefault();
      drawing = false;
    }

    resize();
    window.addEventListener('resize', resize);

    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stop);
    canvas.addEventListener('mouseleave', stop);
    canvas.addEventListener('touchstart', start, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', stop, { passive: false });
    canvas.addEventListener('touchcancel', stop, { passive: false });

    document.getElementById('clearSignatureBtn')?.addEventListener('click', () => {
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
      hasStroke = false;
      saved = '';
      wrap.classList.remove('has-stroke', 'is-saved');
    });

    document.getElementById('saveSignatureBtn')?.addEventListener('click', () => {
      if (!hasStroke) return App.toastError('Draw a signature first');
      saved = canvas.toDataURL('image/png');
      wrap.classList.add('is-saved');
      App.toastSuccess('Signature saved');
    });

    return () => saved;
  }

  async function initRecordCreditPage() {
    const form = document.getElementById('recordCreditForm');
    if (!form) return;

    const select = document.getElementById('customerSelect');
    const errorEl = document.getElementById('formError');

    // Default the due date to a week out — the usual arrangement.
    const dueDate = form.dueDate;
    if (dueDate && !dueDate.value) {
      const d = new Date();
      d.setDate(d.getDate() + 7);
      dueDate.value = d.toISOString().slice(0, 10);
    }
    if (dueDate) dueDate.min = App.todayISO();

    try {
      const customers = await API.customers.list();
      if (customers.length === 0) {
        form.innerHTML = App.emptyState('👤', 'You have no customers yet.',
          '<a class="btn btn-primary btn-sm" href="add-customer.html">Add a customer</a>');
        return;
      }
      select.innerHTML =
        '<option value="">Select a customer…</option>' +
        customers
          .map((c) => `<option value="${c.id}">${App.escapeHtml(c.fullName)}</option>`)
          .join('');

      const preselect = App.getParam('id');
      if (preselect) select.value = preselect;
    } catch (err) {
      App.handleError(err);
      form.innerHTML = App.emptyState('⚠️', err.message);
      return;
    }

    const editor = createItemEditor();
    initQuickItems(editor);
    const getSignature = initSignaturePad();
    const getProductPhoto = initProductPhoto();

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      function fail(message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
        errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      const customerId = select.value;
      if (!customerId) return fail('Please choose a customer.');

      const { items, problems } = editor.collect();
      if (problems.length > 0) return fail(problems[0]);
      if (!form.dueDate.value) return fail('Please choose a due date.');

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const result = await API.customers.addTransaction(customerId, {
            type: 'CREDIT',
            items,
            dueDate: form.dueDate.value,
            notes: form.notes.value.trim(),
            signature: getSignature(),
            productPhoto: getProductPhoto(),
          });
          App.toastSuccess(
            `Credit recorded: ${App.formatCurrency(result.transaction.amount)}`
          );
          window.location.href = `customer-profile.html?id=${customerId}`;
        } catch (err) {
          fail(err.message);
        }
      });
    });
  }

  // ==================================================== transactions feed ==
  function initTransactionsPage() {
    const body = document.getElementById('txBody');
    if (!body) return;

    const typeFilter = document.getElementById('typeFilter');
    const fromInput = document.getElementById('fromDate');
    const toInput = document.getElementById('toDate');
    const wrap = document.getElementById('txWrap');
    const empty = document.getElementById('txEmpty');

    async function load() {
      body.innerHTML = '';
      if (empty) {
        empty.hidden = false;
        empty.innerHTML = App.loadingState('Loading transactions…');
      }
      if (wrap) wrap.hidden = true;

      try {
        const transactions = await API.transactions.list({
          type: typeFilter ? typeFilter.value : '',
          from: fromInput ? fromInput.value : '',
          to: toInput ? toInput.value : '',
        });

        const totals = transactions.reduce(
          (acc, t) => {
            if (t.type === 'CREDIT') acc.credit += t.amount;
            else acc.payments += t.amount;
            return acc;
          },
          { credit: 0, payments: 0 }
        );
        App.setText('txTotalCredit', App.formatCurrency(totals.credit));
        App.setText('txTotalPayments', App.formatCurrency(totals.payments));
        App.setText('txCount', `${transactions.length} transaction${transactions.length === 1 ? '' : 's'}`);

        if (transactions.length === 0) {
          if (empty) empty.innerHTML = App.emptyState('🧾', 'No transactions match those filters.');
          return;
        }

        if (empty) empty.hidden = true;
        if (wrap) wrap.hidden = false;

        body.innerHTML = transactions.map(feedRow).join('');
      } catch (err) {
        App.handleError(err);
        if (empty) empty.innerHTML = App.emptyState('⚠️', err.message);
      }
    }

    function feedRow(t) {
      const isCredit = t.type === 'CREDIT';
      return `<tr>
        <td>${App.formatDateTime(t.createdAt)}</td>
        <td><a href="customer-profile.html?id=${t.customerId}">${App.escapeHtml(t.customerName)}</a></td>
        <td><span class="status-badge ${isCredit ? 'status-owing' : 'status-paid'}">${t.type}</span></td>
        <td class="wrap">
          ${App.escapeHtml(t.description)}
          ${App.itemLinesHtml(t.items)}
        </td>
        <td>${t.dueDate ? App.formatDate(t.dueDate) : '—'}</td>
        <td class="num ${isCredit ? 'amount-credit' : 'amount-payment'}">
          ${isCredit ? '+' : '−'}${App.formatCurrency(t.amount)}
        </td>
      </tr>`;
    }

    [typeFilter, fromInput, toInput].forEach((el) => el?.addEventListener('change', load));
    document.getElementById('clearFilters')?.addEventListener('click', () => {
      if (typeFilter) typeFilter.value = '';
      if (fromInput) fromInput.value = '';
      if (toInput) toInput.value = '';
      load();
    });

    load();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    if (page === 'record-credit') initRecordCreditPage();
    if (page === 'transactions') initTransactionsPage();
  });
})();
