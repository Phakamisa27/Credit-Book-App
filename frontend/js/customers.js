// customers.js — customer list, add, edit, and the customer profile page.

(() => {
  // -------------------------------------------------------------- helpers --
  function balancePill(customer) {
    if (customer.balance > 0) {
      return `<span class="pill owing">${App.formatCurrency(customer.balance)} owing</span>`;
    }
    return '<span class="pill clear">Paid up</span>';
  }

  function customerRow(c) {
    const parts = [`Balance: ${App.formatCurrency(Math.max(0, c.balance))}`];
    if (c.dueDate && c.balance > 0) parts.push(`Due ${App.formatDate(c.dueDate)}`);
    if (c.phone) parts.push(c.phone);

    return `<a class="list-item customer-row" href="customer-profile.html?id=${c.id}">
      <div class="avatar sm">${App.avatarFor(c.fullName, c.gender)}</div>
      <div class="li-main">
        <div class="li-title">${App.escapeHtml(c.fullName)}</div>
        <div class="li-sub">${App.escapeHtml(parts.join(' · '))}</div>
      </div>
      <div class="li-aside">
        ${App.statusBadge(c.status)}
        ${balancePill(c)}
      </div>
    </a>`;
  }

  // ----------------------------------------------------------- list page --
  function initListPage() {
    const container = document.getElementById('customerList');
    if (!container) return;

    const searchInput = document.getElementById('searchInput');
    let statusFilter = 'ALL';
    let searchTimer = null;

    async function load() {
      container.innerHTML = App.loadingState('Loading customers…');
      try {
        const customers = await API.customers.list({
          search: searchInput ? searchInput.value.trim() : '',
          status: statusFilter,
        });

        App.setText('customerCount',
          `${customers.length} customer${customers.length === 1 ? '' : 's'}`);

        if (customers.length === 0) {
          const hasFilter = (searchInput && searchInput.value.trim()) || statusFilter !== 'ALL';
          container.innerHTML = hasFilter
            ? App.emptyState('🔍', 'No customers match your search or filter.')
            : App.emptyState('👥', 'No customers yet.',
                '<a class="btn btn-primary btn-sm" href="add-customer.html">Add your first customer</a>');
          return;
        }

        // Biggest debt first — that is what the owner needs to act on.
        customers.sort((a, b) => b.balance - a.balance);
        container.innerHTML = customers.map(customerRow).join('');
      } catch (err) {
        App.handleError(err);
        container.innerHTML = App.emptyState('⚠️', err.message);
      }
    }

    // Debounced so typing does not fire a request per keystroke.
    searchInput?.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(load, 250);
    });

    document.getElementById('filterBar')?.addEventListener('click', (e) => {
      const chip = e.target.closest('.filter-chip');
      if (!chip) return;
      statusFilter = chip.dataset.filter || 'ALL';
      document.querySelectorAll('.filter-chip').forEach((btn) => {
        btn.classList.toggle('active', btn === chip);
      });
      load();
    });

    load();
  }

  // ------------------------------------------------------ add/edit pages --
  // Both use the same form markup; edit pre-fills it and PATCHes instead.
  function readCustomerForm(form) {
    return {
      fullName: form.fullName.value.trim(),
      phone: form.phone.value.trim(),
      email: form.email.value.trim(),
      address: form.address.value.trim(),
      gender: form.querySelector('input[name="gender"]:checked')?.value || '',
      notes: form.notes.value.trim(),
    };
  }

  function validateCustomer(data) {
    if (!data.fullName) return 'Please enter the customer’s full name.';
    if (!data.phone) return 'Please enter a phone number.';
    if (data.phone.replace(/\D/g, '').length < 10) {
      return 'Please enter a valid 10-digit phone number.';
    }
    return null;
  }

  function initAddPage() {
    const form = document.getElementById('customerForm');
    if (!form) return;

    const errorEl = document.getElementById('formError');
    App.bindPhoneInput(form.phone);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      const data = readCustomerForm(form);
      const problem = validateCustomer(data);
      if (problem) {
        errorEl.textContent = problem;
        errorEl.hidden = false;
        return;
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const customer = await API.customers.create(data);
          App.toastSuccess('Customer added');
          window.location.href = `customer-profile.html?id=${customer.id}`;
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });
  }

  async function initEditPage() {
    const form = document.getElementById('customerForm');
    if (!form) return;

    const id = App.getParam('id');
    const errorEl = document.getElementById('formError');
    App.bindPhoneInput(form.phone);

    if (!id) {
      errorEl.textContent = 'No customer selected.';
      errorEl.hidden = false;
      return;
    }

    try {
      const customer = await API.customers.getById(id);
      form.fullName.value = customer.fullName || '';
      form.phone.value = customer.phone || '';
      form.email.value = customer.email || '';
      form.address.value = customer.address || '';
      form.notes.value = customer.notes || '';
      if (customer.gender) {
        const radio = form.querySelector(`input[name="gender"][value="${customer.gender}"]`);
        if (radio) radio.checked = true;
      }
      App.setText('editingName', customer.fullName);
      const back = document.getElementById('backLink');
      if (back) back.href = `customer-profile.html?id=${id}`;
    } catch (err) {
      errorEl.textContent = err.message;
      errorEl.hidden = false;
      return;
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      const data = readCustomerForm(form);
      const problem = validateCustomer(data);
      if (problem) {
        errorEl.textContent = problem;
        errorEl.hidden = false;
        return;
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.customers.update(id, data);
          App.toastSuccess('Customer updated');
          window.location.href = `customer-profile.html?id=${id}`;
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });
  }

  // -------------------------------------------------------- profile page --
  function initProfilePage() {
    const root = document.getElementById('profileRoot');
    if (!root) return;

    const id = App.getParam('id');
    if (!id) {
      root.innerHTML = App.emptyState('🤔', 'No customer selected.');
      return;
    }

    let customer = null;

    function renderSummary(c) {
      App.setText('profileName', c.fullName);
      App.setText('profilePhone', c.phone || 'No phone number');
      App.setText('summaryTotalCredit', App.formatCurrency(c.totalCredit));
      App.setText('summaryTotalPaid', App.formatCurrency(c.totalPaid));
      App.setText('summaryBalance', App.formatCurrency(Math.max(0, c.balance)));
      App.setText('summaryDueDate', c.dueDate ? App.formatDate(c.dueDate) : '—');
      App.setHtml('summaryStatus', App.statusBadge(c.status));

      const avatar = document.getElementById('profileAvatar');
      if (avatar) avatar.textContent = App.avatarFor(c.fullName, c.gender);

      const meta = document.getElementById('profileMeta');
      if (meta) {
        const bits = [];
        if (c.address) bits.push(`📍 ${c.address}`);
        if (c.email) bits.push(`✉️ ${c.email}`);
        if (c.notes) bits.push(c.notes);
        meta.textContent = bits.join(' · ');
        meta.hidden = bits.length === 0;
      }

      const box = document.getElementById('balanceBox');
      if (box) {
        box.classList.toggle('owing', c.balance > 0);
        box.querySelector('.value').textContent = App.formatCurrency(Math.max(0, c.balance));
        box.querySelector('.label').textContent =
          c.balance > 0 ? 'Current Balance' : 'Account is paid up';
      }

      // Only offer "Record Payment" when there is something to pay off.
      const payBtn = document.getElementById('recordPaymentBtn');
      if (payBtn) payBtn.disabled = c.balance <= 0;

      const editLink = document.getElementById('editCustomerLink');
      if (editLink) editLink.href = `edit-customer.html?id=${c.id}`;
      const creditLink = document.getElementById('addCreditLink');
      if (creditLink) creditLink.href = `record-credit.html?id=${c.id}`;
    }

    // Date | Type | Description | Amount | Balance — the paper credit book,
    // with the running balance the backend calculated.
    function renderHistory(transactions) {
      const body = document.getElementById('historyBody');
      const wrap = document.getElementById('historyWrap');
      const empty = document.getElementById('historyEmpty');
      if (!body) return;

      if (transactions.length === 0) {
        if (wrap) wrap.hidden = true;
        if (empty) {
          empty.hidden = false;
          empty.innerHTML = App.emptyState('🧾', 'No transactions yet.');
        }
        return;
      }

      if (wrap) wrap.hidden = false;
      if (empty) empty.hidden = true;

      body.innerHTML = transactions
        .map((t) => {
          const isCredit = t.type === 'CREDIT';
          const extras = [];
          if (isCredit && t.dueDate) extras.push(`Due ${App.formatDate(t.dueDate)}`);
          if (t.signature) extras.push('Signed ✓');
          if (t.productPhoto) extras.push('Photo ✓');

          return `<tr>
            <td>${App.formatDateShort(t.createdAt)}</td>
            <td><span class="status-badge ${isCredit ? 'status-owing' : 'status-paid'}">${t.type}</span></td>
            <td class="wrap">
              ${App.escapeHtml(t.description)}
              ${App.itemLinesHtml(t.items)}
              ${extras.length ? `<div class="li-sub">${App.escapeHtml(extras.join(' · '))}</div>` : ''}
            </td>
            <td class="num ${isCredit ? 'amount-credit' : 'amount-payment'}">
              ${isCredit ? '' : '−'}${App.formatCurrency(t.amount)}
            </td>
            <td class="num">${App.formatCurrency(Math.max(0, t.runningBalance))}</td>
            <td class="num">
              <button type="button" class="link-btn text-danger" data-delete-tx="${t.id}">Delete</button>
            </td>
          </tr>`;
        })
        .join('');
    }

    async function load() {
      try {
        const { customer: c, transactions } = await API.customers.transactions(id);
        customer = c;
        renderSummary(c);
        renderHistory(transactions);
      } catch (err) {
        App.handleError(err);
        root.innerHTML = App.emptyState('⚠️', err.message);
      }
    }

    // ---- payment modal ----
    const paymentModal = Modal.create('paymentModal');

    document.getElementById('recordPaymentBtn')?.addEventListener('click', () => {
      if (!customer) return;
      const form = document.getElementById('paymentForm');
      form.reset();
      App.setText('paymentBalanceHint',
        `${customer.fullName} owes ${App.formatCurrency(customer.balance)}`);
      // Pre-fill with the full balance — settling in full is the common case.
      form.amount.value = customer.balance.toFixed(2);
      form.amount.max = customer.balance.toFixed(2);
      paymentModal.open();
    });

    document.getElementById('paymentForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const errorEl = document.getElementById('paymentError');
      errorEl.hidden = true;

      const amount = parseFloat(form.amount.value);
      if (!amount || amount <= 0) {
        errorEl.textContent = 'Enter an amount greater than zero.';
        errorEl.hidden = false;
        return;
      }
      if (amount > customer.balance) {
        errorEl.textContent =
          `That is more than the ${App.formatCurrency(customer.balance)} owed.`;
        errorEl.hidden = false;
        return;
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.customers.addTransaction(id, {
            type: 'PAYMENT',
            amount,
            description: form.description.value.trim() || 'Payment received',
            notes: form.notes.value.trim(),
          });
          paymentModal.close();
          App.toastSuccess('Payment recorded');
          load();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });

    // ---- reminder modal ----
    const reminderModal = Modal.create('reminderModal');

    document.getElementById('setReminderBtn')?.addEventListener('click', () => {
      if (!customer) return;
      const form = document.getElementById('reminderForm');
      form.reset();
      form.amount.value = Math.max(0, customer.balance).toFixed(2);
      form.dueDate.value = customer.dueDate || App.todayISO();
      App.setText('reminderCustomerName', customer.fullName);
      reminderModal.open();
    });

    document.getElementById('reminderForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const errorEl = document.getElementById('reminderError');
      errorEl.hidden = true;

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.reminders.create({
            customerId: Number(id),
            amount: parseFloat(form.amount.value),
            dueDate: form.dueDate.value,
            notes: form.notes.value.trim(),
          });
          reminderModal.close();
          App.toastSuccess('Reminder set');
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });

    // ---- delete a transaction (fixes a mis-keyed amount) ----
    document.getElementById('historyBody')?.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-delete-tx]');
      if (!btn) return;
      if (!confirm('Delete this transaction? The balance will be recalculated.')) return;
      try {
        await API.transactions.remove(btn.dataset.deleteTx);
        App.toastSuccess('Transaction deleted');
        load();
      } catch (err) {
        App.handleError(err);
      }
    });

    // ---- delete the customer ----
    document.getElementById('deleteCustomerBtn')?.addEventListener('click', async () => {
      if (!customer) return;
      const warning = customer.balance > 0
        ? `${customer.fullName} still owes ${App.formatCurrency(customer.balance)}.\n\n`
        : '';
      if (!confirm(`${warning}Delete ${customer.fullName} and all their transactions? This cannot be undone.`)) {
        return;
      }
      try {
        await API.customers.remove(id);
        App.toastSuccess('Customer deleted');
        window.location.href = 'customers.html';
      } catch (err) {
        App.handleError(err);
      }
    });

    load();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    if (page === 'customers') initListPage();
    if (page === 'add-customer') initAddPage();
    if (page === 'edit-customer') initEditPage();
    if (page === 'customer-profile') initProfilePage();
  });
})();
