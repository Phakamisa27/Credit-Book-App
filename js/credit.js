// credit.js — record credit form, transactions feed, and reports

const Credit = (() => {
  let managing = false;

  // Render the owner's quick items. Clicking a chip fills the form; in "Edit"
  // mode each chip shows a delete button. A dashed "Add Item" chip lets the
  // owner add their own products (e.g. Perfume), since shops differ.
  function renderQuickItems(form) {
    const chips = document.getElementById('quickItems');
    if (!chips) return;
    const items = Storage.getItems();

    chips.classList.toggle('managing', managing);

    let html = items
      .map(
        (it) => `<span class="qi-chip" data-id="${it.id}">
          <button type="button" class="pill clear qi-fill"
            data-item="${App.escapeHtml(it.name)}" data-price="${it.price}">
            ${App.escapeHtml(it.name)} · ${App.formatCurrency(it.price)}
          </button>
          <button type="button" class="qi-del" data-id="${it.id}" aria-label="Delete item">×</button>
        </span>`
      )
      .join('');

    html += `<button type="button" class="pill add-item" id="addItemBtn">＋ Add Item</button>`;
    chips.innerHTML = html;

    chips.querySelectorAll('.qi-fill').forEach((b) =>
      b.addEventListener('click', () => {
        if (managing) return;
        form.itemName.value = b.dataset.item;
        form.amount.value = b.dataset.price;
      })
    );

    chips.querySelectorAll('.qi-del').forEach((b) =>
      b.addEventListener('click', () => {
        Storage.deleteItem(b.dataset.id);
        App.toast('Item removed');
        renderQuickItems(form);
      })
    );

    document.getElementById('addItemBtn')?.addEventListener('click', () => addItem(form));
  }

  function addItem(form) {
    const name = prompt('Item name (e.g. Perfume):', '');
    if (name === null) return;
    if (!name.trim()) return App.toast('Enter an item name');
    const priceInput = prompt(`Price for "${name.trim()}" (R):`, '');
    if (priceInput === null) return;
    const price = parseFloat(priceInput);
    if (!price || price <= 0) return App.toast('Enter a valid price');
    Storage.addItem({ name, price });
    App.toast('Item added');
    renderQuickItems(form);
  }

  function txBadgesHtml(tx) {
    let html = '';
    if (tx.signature) html += '<span class="signature-badge">Signature Captured ✓</span>';
    if (tx.productPhoto) html += '<span class="product-photo-badge">Product Photo Captured ✓</span>';
    return html;
  }

  function initProductPhoto() {
    const input = document.getElementById('productPhotoInput');
    const empty = document.getElementById('productPhotoEmpty');
    const preview = document.getElementById('productPhotoPreview');
    const previewImg = document.getElementById('productPhotoPreviewImg');
    const trigger = document.getElementById('productPhotoTrigger');
    const changeBtn = document.getElementById('changePhotoBtn');
    const removeBtn = document.getElementById('removePhotoBtn');
    if (!input) return () => '';

    let productPhoto = '';

    function showPreview(base64) {
      productPhoto = base64;
      if (previewImg) previewImg.src = base64;
      if (preview) preview.hidden = false;
      if (empty) empty.hidden = true;
    }

    function clearPhoto() {
      productPhoto = '';
      input.value = '';
      if (previewImg) previewImg.removeAttribute('src');
      if (preview) preview.hidden = true;
      if (empty) empty.hidden = false;
    }

    function handleFile(file) {
      if (!file || !file.type.startsWith('image/')) {
        App.toast('Please select an image file');
        input.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = () => showPreview(reader.result);
      reader.onerror = () => App.toast('Could not read that image');
      reader.readAsDataURL(file);
    }

    trigger?.addEventListener('click', () => input.click());
    changeBtn?.addEventListener('click', () => input.click());
    removeBtn?.addEventListener('click', clearPhoto);
    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (file) handleFile(file);
      input.value = '';
    });

    return () => productPhoto;
  }

  function initSignaturePad() {
    const canvas = document.getElementById('signatureCanvas');
    const wrap = document.getElementById('signatureWrap');
    const clearBtn = document.getElementById('clearSignatureBtn');
    const saveBtn = document.getElementById('saveSignatureBtn');
    if (!canvas || !wrap) return () => '';

    const ctx = canvas.getContext('2d');
    let savedSignature = '';
    let isDrawing = false;
    let hasStroke = false;
    let lastX = 0;
    let lastY = 0;

    function resizeCanvas() {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const imageData = savedSignature || (hasStroke ? canvas.toDataURL('image/png') : null);

      canvas.width = Math.floor(rect.width * dpr);
      canvas.height = Math.floor(rect.height * dpr);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      ctx.strokeStyle = '#1a2e24';
      ctx.lineWidth = 2.2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      if (imageData) {
        const img = new Image();
        img.onload = () => {
          ctx.drawImage(img, 0, 0, rect.width, rect.height);
        };
        img.src = imageData;
      }
    }

    function getPos(e) {
      const rect = canvas.getBoundingClientRect();
      const source = e.touches ? e.touches[0] : e;
      return {
        x: source.clientX - rect.left,
        y: source.clientY - rect.top,
      };
    }

    function startDraw(e) {
      if (e.cancelable) e.preventDefault();
      isDrawing = true;
      const { x, y } = getPos(e);
      lastX = x;
      lastY = y;
    }

    function draw(e) {
      if (!isDrawing) return;
      if (e.cancelable) e.preventDefault();
      const { x, y } = getPos(e);
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(x, y);
      ctx.stroke();
      lastX = x;
      lastY = y;
      if (!hasStroke) {
        hasStroke = true;
        wrap.classList.add('has-stroke');
      }
    }

    function stopDraw(e) {
      if (e?.cancelable) e.preventDefault();
      isDrawing = false;
    }

    function clearSignature() {
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
      hasStroke = false;
      savedSignature = '';
      wrap.classList.remove('has-stroke', 'is-saved');
    }

    function saveSignature() {
      if (!hasStroke) {
        App.toast('Draw a signature first');
        return;
      }
      savedSignature = canvas.toDataURL('image/png');
      wrap.classList.add('is-saved');
      App.toast('Signature saved');
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    canvas.addEventListener('mousedown', startDraw);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDraw);
    canvas.addEventListener('mouseleave', stopDraw);

    canvas.addEventListener('touchstart', startDraw, { passive: false });
    canvas.addEventListener('touchmove', draw, { passive: false });
    canvas.addEventListener('touchend', stopDraw, { passive: false });
    canvas.addEventListener('touchcancel', stopDraw, { passive: false });

    clearBtn?.addEventListener('click', clearSignature);
    saveBtn?.addEventListener('click', saveSignature);

    return () => savedSignature;
  }

  // ---- Record credit page (record-credit.html) ----
  function initRecordPage() {
    const form = document.getElementById('recordCreditForm');
    if (!form) return;

    const select = document.getElementById('customerSelect');
    const customers = Storage.getCustomers();
    if (customers.length === 0) {
      form.innerHTML = `<div class="empty"><span class="emoji">👤</span>
        No customers yet. <a href="add-customer.html">Add a customer</a> first.</div>`;
      return;
    }
    if (select) {
      select.innerHTML =
        '<option value="">Select a customer…</option>' +
        customers.map((c) => `<option value="${c.id}">${App.escapeHtml(c.name)}</option>`).join('');
      const preselect = App.getParam('id');
      if (preselect) select.value = preselect;
    }

    renderQuickItems(form);
    const getSavedSignature = initSignaturePad();
    const getProductPhoto = initProductPhoto();

    document.getElementById('manageItemsBtn')?.addEventListener('click', (e) => {
      managing = !managing;
      e.target.textContent = managing ? 'Done' : 'Edit';
      renderQuickItems(form);
    });

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const customerId = form.customer.value;
      const itemName = form.itemName.value.trim();
      const amount = parseFloat(form.amount.value);
      const dueDate = form.dueDate.value;
      const signature = getSavedSignature();
      const productPhoto = getProductPhoto();
      if (!customerId) return App.toast('Please choose a customer');
      if (!itemName) return App.toast('Enter an item');
      if (!amount || amount <= 0) return App.toast('Enter a valid amount');
      if (!dueDate) return App.toast('Please select a due date');

      Storage.addTransaction({
        customerId,
        type: 'credit',
        itemName,
        amount,
        dueDate,
        signature,
        productPhoto,
      });
      App.toast('Credit recorded');
      setTimeout(() => (window.location.href = `customer-profile.html?id=${customerId}`), 600);
    });
  }

  // ---- Transactions feed (transactions.html) ----
  function initTransactionsPage() {
    const list = document.getElementById('txList');
    if (!list) return;
    const txs = Storage.getTransactions().sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    if (txs.length === 0) {
      list.innerHTML = `<div class="empty"><span class="emoji">🧾</span>No transactions yet.</div>`;
      return;
    }
    list.innerHTML = txs
      .map((t) => {
        const c = Storage.getCustomer(t.customerId);
        const isCredit = t.type === 'credit';
        const dueLine =
          isCredit && t.dueDate
            ? ` · Due ${App.formatDueDate(t.dueDate)}`
            : '';
        return `<a class="list-item" href="customer-profile.html?id=${t.customerId}">
          <div class="li-icon">${isCredit ? App.itemEmoji(t.itemName) : '💵'}</div>
          <div class="li-main">
            <div class="li-title">${App.escapeHtml(t.itemName)}</div>
            <div class="li-sub">${c ? App.escapeHtml(c.name) : 'Unknown'} · ${App.formatDate(t.createdAt)}${dueLine}</div>
            ${txBadgesHtml(t)}
          </div>
          <span class="li-amount ${isCredit ? 'credit' : 'payment'}">
            ${isCredit ? '+' : '−'}${App.formatCurrency(t.amount)}
          </span>
        </a>`;
      })
      .join('');
  }

  // ---- Reports (reports.html) ----
  function initReportsPage() {
    const root = document.getElementById('reportsRoot');
    if (!root) return;

    const customers = Storage.getCustomers();
    const txs = Storage.getTransactions();
    const totalCredit = txs.filter((t) => t.type === 'credit').reduce((s, t) => s + t.amount, 0);
    const totalPayments = txs.filter((t) => t.type === 'payment').reduce((s, t) => s + t.amount, 0);

    App.setText('repOutstanding', App.formatCurrency(Storage.getTotalOutstanding()));
    App.setText('repCustomers', String(customers.length));
    App.setText('repCredit', App.formatCurrency(totalCredit));
    App.setText('repPayments', App.formatCurrency(totalPayments));

    const debtors = customers
      .filter((c) => (c.balance || 0) > 0)
      .sort((a, b) => b.balance - a.balance)
      .slice(0, 5);

    const list = document.getElementById('topDebtors');
    if (list) {
      if (debtors.length === 0) {
        list.innerHTML = `<div class="empty"><span class="emoji">🎉</span>No outstanding balances!</div>`;
      } else {
        list.innerHTML = debtors
          .map(
            (c) => `<a class="list-item" href="customer-profile.html?id=${c.id}">
              <div class="avatar sm">${App.avatarFor(c.name, c.gender)}</div>
              <div class="li-main"><div class="li-title">${App.escapeHtml(c.name)}</div></div>
              <span class="li-amount credit">${App.formatCurrency(c.balance)}</span>
            </a>`
          )
          .join('');
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    if (page === 'record-credit') initRecordPage();
    if (page === 'transactions') initTransactionsPage();
    if (page === 'reports') initReportsPage();
  });

  return {};
})();
