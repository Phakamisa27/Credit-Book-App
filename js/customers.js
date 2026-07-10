// customers.js — customer list, add-customer form, and profile rendering

const Customers = (() => {
  let activeStatusFilter = 'all';

  function balancePill(balance) {
    if (balance > 0) return `<span class="pill owing">${App.formatCurrency(balance)} owing</span>`;
    return `<span class="pill clear">Paid up</span>`;
  }

  function matchesStatusFilter(customer, filter) {
    const dueInfo = Storage.getCustomerDueInfo(customer);
    if (filter === 'all') return true;
    if (filter === 'paid') return dueInfo.status === 'Paid';
    if (filter === 'due-today') return dueInfo.status === 'Due Today';
    if (filter === 'overdue') return dueInfo.status === 'Overdue';
    return true;
  }

  // ---- List page (customers.html) ----
  function renderList(searchQuery = '') {
    const container = document.getElementById('customerList');
    if (!container) return;
    const q = searchQuery.trim().toLowerCase();
    let customers = Storage.getCustomers();
    if (q) {
      customers = customers.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.phone || '').toLowerCase().includes(q) ||
          (c.phone || '').replace(/\s/g, '').includes(q.replace(/\s/g, '')) ||
          (c.area || '').toLowerCase().includes(q)
      );
    }
    if (activeStatusFilter !== 'all') {
      customers = customers.filter((c) => matchesStatusFilter(c, activeStatusFilter));
    }
    customers.sort((a, b) => (b.balance || 0) - (a.balance || 0));

    if (customers.length === 0) {
      const emptyMsg =
        q || activeStatusFilter !== 'all'
          ? 'No customers match your search or filter.'
          : 'No customers yet. Add your first one!';
      container.innerHTML = `<div class="empty"><span class="emoji">👥</span>${emptyMsg}</div>`;
      return;
    }

    container.innerHTML = customers
      .map((c) => {
        const bal = c.balance || 0;
        const dueInfo = Storage.getCustomerDueInfo(c);
        const subParts = [`Balance: ${App.formatCurrency(Math.max(0, bal))}`];
        if (dueInfo.dueDate) {
          subParts.push(`Due Date: ${App.formatDueDate(dueInfo.dueDate)}`);
        }
        const sub = subParts.join(' · ');
        const badge = dueInfo.status ? App.statusBadge(dueInfo.status) : '';
        return `<a class="list-item customer-row" href="customer-profile.html?id=${c.id}">
          <div class="avatar sm">${App.avatarFor(c.name, c.gender)}</div>
          <div class="li-main">
            <div class="li-title">${App.escapeHtml(c.name)}</div>
            <div class="li-sub">${App.escapeHtml(sub)}</div>
          </div>
          <div class="li-aside">
            ${badge}
            ${balancePill(bal)}
          </div>
        </a>`;
      })
      .join('');
  }

  async function initListPage() {
    const container = document.getElementById('customerList');
    if (container) {
      container.innerHTML = '<div class="empty"><span class="emoji">⏳</span>Loading customers…</div>';
    }

    try {
      const customers = await API.getCustomers();
      Storage.syncCustomersFromApi(customers);
      Storage.recomputeBalances();
      renderList();
    } catch (err) {
      App.toast(err.message || API.OFFLINE_MSG);
      if (container) {
        container.innerHTML = `<div class="empty"><span class="emoji">⚠️</span>${App.escapeHtml(err.message || API.OFFLINE_MSG)}</div>`;
      }
    }

    const search = document.getElementById('searchInput');
    if (search) search.addEventListener('input', (e) => renderList(e.target.value));

    document.getElementById('filterBar')?.addEventListener('click', (e) => {
      const chip = e.target.closest('.filter-chip');
      if (!chip) return;
      activeStatusFilter = chip.dataset.filter || 'all';
      document.querySelectorAll('.filter-chip').forEach((btn) => {
        btn.classList.toggle('active', btn === chip);
      });
      renderList(search?.value || '');
    });
  }

  // ---- Add customer page (add-customer.html) ----
  function initAddPage() {
    const form = document.getElementById('addCustomerForm');
    if (!form) return;
    App.bindPhoneInput(form.phone);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = form.name.value.trim();
      const phone = App.formatPhoneNumber(form.phone.value);
      if (!name) {
        App.toast('Please enter a name');
        return;
      }
      if (!phone.trim()) {
        App.toast('Please enter a phone number');
        return;
      }

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      try {
        const created = await API.createCustomer({
          name,
          phone,
          area: form.area.value,
        });
        Storage.syncCustomerFromApi({
          ...created,
          gender: form.gender.value,
        });
        Storage.recomputeBalances();
        App.toast('Customer added');
        setTimeout(() => (window.location.href = 'customers.html'), 600);
      } catch (err) {
        App.toast(err.message || API.OFFLINE_MSG);
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // ---- Profile page (customer-profile.html) ----
  function initPhotoModal() {
    const modal = document.getElementById('photoModal');
    const modalImg = document.getElementById('photoModalImg');
    const backdrop = document.getElementById('photoModalBackdrop');
    const closeBtn = document.getElementById('photoModalClose');
    if (!modal || !modalImg) return;

    function closeModal() {
      modal.hidden = true;
      modalImg.removeAttribute('src');
      document.body.style.overflow = '';
    }

    function openModal(src) {
      modalImg.src = src;
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    backdrop?.addEventListener('click', closeModal);
    closeBtn?.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !modal.hidden) closeModal();
    });

    return openModal;
  }

  async function loadProfilePage() {
    const root = document.getElementById('profileRoot');
    if (!root) return;
    const id = App.getParam('id');
    if (!id) {
      root.innerHTML = `<div class="empty"><span class="emoji">🤔</span>Customer not found.</div>`;
      return;
    }

    const historyList = document.getElementById('historyList');
    if (historyList) {
      historyList.innerHTML = '<div class="empty"><span class="emoji">⏳</span>Loading customer…</div>';
    }

    let customer;
    try {
      customer = await API.getCustomerById(id);
      const cached = Storage.getCustomer(id);
      Storage.syncCustomerFromApi({
        ...customer,
        gender: cached?.gender || customer.gender || '',
      });
      Storage.recomputeBalances();
      customer = Storage.getCustomer(id);
    } catch (err) {
      App.toast(err.message || API.OFFLINE_MSG);
      root.innerHTML = `<div class="empty"><span class="emoji">⚠️</span>${App.escapeHtml(err.message || API.OFFLINE_MSG)}</div>`;
      return;
    }

    if (!customer) {
      root.innerHTML = `<div class="empty"><span class="emoji">🤔</span>Customer not found.</div>`;
      return;
    }

    renderProfile(customer);
    const openPhotoModal = initPhotoModal();

    document.getElementById('historyList')?.addEventListener('click', (e) => {
      const thumb = e.target.closest('.tx-photo-thumb');
      if (!thumb) return;
      e.preventDefault();
      e.stopPropagation();
      const tx = Storage.getCustomerTransactions(customer.id).find((t) => t.id === thumb.dataset.txId);
      if (tx?.productPhoto) openPhotoModal(tx.productPhoto);
    });

    document.getElementById('recordCreditBtn')?.addEventListener('click', () => {
      window.location.href = `record-credit.html?id=${id}`;
    });
    document.getElementById('markPaymentBtn')?.addEventListener('click', () => openPayment(id));
    document.getElementById('remindBtn')?.addEventListener('click', () => {
      window.location.href = `reminders.html?id=${id}`;
    });
    document.getElementById('deleteBtn')?.addEventListener('click', async () => {
      if (!confirm(`Delete ${customer.name} and all their records?`)) return;
      try {
        await API.deleteCustomer(id);
        Storage.deleteCustomer(id);
        window.location.href = 'customers.html';
      } catch (err) {
        App.toast(err.message || API.OFFLINE_MSG);
      }
    });
  }

  function renderProfile(customer) {
    const bal = customer.balance || 0;
    const totals = Storage.getCustomerCreditTotals(customer.id);
    const dueInfo = Storage.getCustomerDueInfo(customer);

    App.setText('profileName', customer.name);
    App.setText('profilePhone', customer.phone || 'No phone number');
    const avatarEl = document.getElementById('profileAvatar');
    if (avatarEl) avatarEl.textContent = App.avatarFor(customer.name, customer.gender);

    const meta = document.getElementById('profileMeta');
    if (meta) {
      const bits = [];
      if (customer.gender === 'male') bits.push('Male');
      else if (customer.gender === 'female') bits.push('Female');
      if (customer.area) bits.push(`📍 ${App.escapeHtml(customer.area)}`);
      if (customer.notes) bits.push(App.escapeHtml(customer.notes));
      meta.innerHTML = bits.join(' · ');
      meta.style.display = bits.length ? '' : 'none';
    }

    App.setText('totalCredit', App.formatCurrency(totals.totalCredit));
    App.setText('totalPaid', App.formatCurrency(totals.totalPaid));
    App.setText('remainingBalance', App.formatCurrency(Math.max(0, bal)));
    App.setText('profileDueDate', dueInfo.dueDate ? App.formatDueDate(dueInfo.dueDate) : '—');

    const statusEl = document.getElementById('profileStatus');
    if (statusEl) {
      statusEl.innerHTML = dueInfo.status ? App.statusBadge(dueInfo.status) : '<span class="muted">—</span>';
    }

    const balBox = document.getElementById('balanceBox');
    if (balBox) {
      balBox.classList.toggle('owing', bal > 0);
      balBox.querySelector('.value').textContent = App.formatCurrency(Math.max(0, bal));
      balBox.querySelector('.label').textContent = bal > 0 ? 'Current Balance' : 'Account is paid up';
    }

    const history = Storage.getCustomerTransactions(customer.id);
    const list = document.getElementById('historyList');
    if (!list) return;
    if (history.length === 0) {
      list.innerHTML = `<div class="empty"><span class="emoji">🧾</span>No transactions yet.</div>`;
      return;
    }
    list.innerHTML = history
      .map((t) => {
        const isCredit = t.type === 'credit';
        const subParts = [App.formatDate(t.createdAt)];
        if (isCredit && t.dueDate) subParts.push(`Due ${App.formatDueDate(t.dueDate)}`);
        const sub = subParts.join(' · ');
        const txStatus =
          isCredit && t.dueDate
            ? App.statusBadge(Storage.getDueStatus(t.dueDate, bal))
            : '';
        const badges = [
          txStatus,
          t.signature ? '<span class="signature-badge">Signature Captured ✓</span>' : '',
          t.productPhoto ? '<span class="product-photo-badge">Product Photo Captured ✓</span>' : '',
        ].filter(Boolean).join('');
        const photoThumb = t.productPhoto
          ? `<button type="button" class="tx-photo-thumb" data-tx-id="${t.id}" aria-label="View product photo">
              <img src="${t.productPhoto}" alt="Product photo thumbnail" />
            </button>`
          : '';
        return `<li class="list-item">
          <div class="li-icon">${isCredit ? App.itemEmoji(t.itemName) : '💵'}</div>
          <div class="li-main">
            <div class="li-title">${App.escapeHtml(t.itemName)}</div>
            <div class="li-sub">${App.escapeHtml(sub)}</div>
            ${badges ? `<div class="tx-badges">${badges}</div>` : ''}
            ${photoThumb}
          </div>
          <span class="li-amount ${isCredit ? 'credit' : 'payment'}">
            ${isCredit ? '+' : '−'}${App.formatCurrency(t.amount)}
          </span>
        </li>`;
      })
      .join('');
  }

  function openPayment(customerId) {
    const customer = Storage.getCustomer(customerId);
    const bal = customer.balance || 0;
    const input = prompt(
      `Record a payment from ${customer.name}.\nCurrent balance: ${App.formatCurrency(Math.max(0, bal))}\n\nEnter amount (R):`,
      bal > 0 ? bal.toFixed(2) : ''
    );
    if (input === null) return;
    const amount = parseFloat(input);
    if (!amount || amount <= 0) {
      App.toast('Enter a valid amount');
      return;
    }
    Storage.addTransaction({ customerId, type: 'payment', itemName: 'Payment received', amount });
    App.toast('Payment recorded');
    renderProfile(Storage.getCustomer(customerId));
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    if (page === 'customers') initListPage();
    if (page === 'add-customer') initAddPage();
    if (page === 'customer-profile') loadProfilePage();
  });

  return { renderList };
})();
