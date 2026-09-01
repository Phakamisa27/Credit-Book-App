// reminders.js — payment reminders, plus sending them via WhatsApp or SMS.
//
// Sending is deliberately manual: the app builds the message and hands it to
// WhatsApp or the phone's SMS app. No gateway, no API keys, no monthly bill.

(() => {
  const MESSAGES = {
    en: (name, amount, shop, due) =>
      `Hi ${name}, you have an outstanding balance of ${amount} at ${shop}` +
      `${due ? `, due ${due}` : ''}. Please settle when you can. Thank you!`,
    zu: (name, amount, shop, due) =>
      `Sawubona ${name}, unesikweletu esingu-${amount} kwa-${shop}` +
      `${due ? `, esifanele sikhokhwe ngo-${due}` : ''}. Sicela ukhokhe uma usukwazi. Ngiyabonga!`,
  };

  let language = 'en';
  let businessName = 'our shop';
  let reminders = [];
  let customers = [];

  function firstName(fullName) {
    return String(fullName || '').split(' ')[0];
  }

  function buildMessage(reminder) {
    const build = MESSAGES[language] || MESSAGES.en;
    return build(
      firstName(reminder.customerName),
      App.formatCurrency(reminder.amount),
      businessName,
      App.formatDate(reminder.dueDate)
    );
  }

  // 074… -> 2774… so wa.me accepts it.
  function toInternational(phone) {
    const digits = String(phone || '').replace(/\D/g, '');
    if (!digits) return '';
    if (digits.startsWith('0')) return `27${digits.slice(1)}`;
    if (digits.startsWith('27')) return digits;
    return digits;
  }

  function reminderCard(r) {
    const closed = r.status === 'DONE' || r.status === 'CANCELLED';
    return `<div class="list-item reminder-item ${closed ? 'is-closed' : ''}">
      <div class="li-icon">${r.urgency === 'OVERDUE' ? '⚠️' : '🔔'}</div>
      <div class="li-main">
        <div class="li-title">
          <a href="customer-profile.html?id=${r.customerId}">${App.escapeHtml(r.customerName)}</a>
        </div>
        <div class="li-sub">
          Owes ${App.formatCurrency(r.amount)} · Due ${App.formatDate(r.dueDate)}
          ${r.customerPhone ? ` · ${App.escapeHtml(r.customerPhone)}` : ''}
        </div>
        ${r.notes ? `<div class="li-sub">${App.escapeHtml(r.notes)}</div>` : ''}
        <div class="reminder-actions">
          <button type="button" class="link-btn" data-send="whatsapp" data-id="${r.id}">💬 WhatsApp</button>
          <button type="button" class="link-btn" data-send="sms" data-id="${r.id}">✉️ SMS</button>
          ${closed
            ? `<button type="button" class="link-btn" data-reopen="${r.id}">Reopen</button>`
            : `<button type="button" class="link-btn" data-done="${r.id}">Mark paid</button>`}
          <button type="button" class="link-btn text-danger" data-delete="${r.id}">Delete</button>
        </div>
      </div>
      <div class="li-aside">
        ${App.statusBadge(r.urgency)}
        ${closed ? App.statusBadge(r.status) : ''}
      </div>
    </div>`;
  }

  function render() {
    const list = document.getElementById('reminderList');
    if (!list) return;

    const overdue = reminders.filter((r) => r.urgency === 'OVERDUE').length;
    const dueSoon = reminders.filter(
      (r) => r.urgency === 'DUE_TODAY' || r.urgency === 'DUE_SOON'
    ).length;
    App.setText('statOverdueReminders', String(overdue));
    App.setText('statDueSoonReminders', String(dueSoon));

    list.innerHTML = reminders.length
      ? reminders.map(reminderCard).join('')
      : App.emptyState('🔕', 'No reminders yet. Set one from a customer’s profile or with “New reminder”.');
  }

  function updatePreview() {
    const preview = document.getElementById('messagePreview');
    if (!preview) return;

    // Show the message for whoever is most urgent — usually who you'd contact.
    const target = reminders.find((r) => r.urgency === 'OVERDUE') || reminders[0];
    if (!target) {
      preview.textContent = 'Set a reminder to see the message preview.';
      return;
    }
    preview.textContent = buildMessage(target);
  }

  async function load() {
    const list = document.getElementById('reminderList');
    if (list) list.innerHTML = App.loadingState('Loading reminders…');

    try {
      const statusFilter = document.getElementById('statusFilter');
      [reminders, customers] = await Promise.all([
        API.reminders.list({ status: statusFilter ? statusFilter.value : 'OPEN' }),
        API.customers.list(),
      ]);

      const user = API.getCachedUser();
      businessName = (user && user.businessName) || 'our shop';

      render();
      updatePreview();
    } catch (err) {
      App.handleError(err);
      if (list) list.innerHTML = App.emptyState('⚠️', err.message);
    }
  }

  function initNewReminderModal() {
    const modal = Modal.create('newReminderModal');
    const form = document.getElementById('newReminderForm');
    if (!form) return;

    document.getElementById('newReminderBtn')?.addEventListener('click', () => {
      if (customers.length === 0) {
        return App.toastError('Add a customer first.');
      }
      form.reset();
      form.customerId.innerHTML = customers
        .map(
          (c) =>
            `<option value="${c.id}" data-balance="${c.balance}" data-due="${c.dueDate || ''}">
              ${App.escapeHtml(c.fullName)} — ${App.formatCurrency(Math.max(0, c.balance))}
            </option>`
        )
        .join('');
      form.dueDate.value = App.todayISO();
      syncAmountToCustomer();
      modal.open();
    });

    // Pre-fill the amount with what that customer actually owes.
    function syncAmountToCustomer() {
      const option = form.customerId.selectedOptions[0];
      if (!option) return;
      form.amount.value = Math.max(0, Number(option.dataset.balance || 0)).toFixed(2);
      if (option.dataset.due) form.dueDate.value = option.dataset.due;
    }

    form.customerId.addEventListener('change', syncAmountToCustomer);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const errorEl = document.getElementById('newReminderError');
      errorEl.hidden = true;

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.reminders.create({
            customerId: Number(form.customerId.value),
            amount: parseFloat(form.amount.value),
            dueDate: form.dueDate.value,
            notes: form.notes.value.trim(),
          });
          modal.close();
          App.toastSuccess('Reminder created');
          load();
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });
  }

  function initListActions() {
    document.getElementById('reminderList')?.addEventListener('click', async (e) => {
      const sendBtn = e.target.closest('[data-send]');
      if (sendBtn) {
        const reminder = reminders.find((r) => String(r.id) === sendBtn.dataset.id);
        if (!reminder) return;
        if (!reminder.customerPhone) return App.toastError('That customer has no phone number.');

        const message = encodeURIComponent(buildMessage(reminder));
        if (sendBtn.dataset.send === 'whatsapp') {
          window.open(`https://wa.me/${toInternational(reminder.customerPhone)}?text=${message}`, '_blank');
        } else {
          window.location.href = `sms:${reminder.customerPhone}?body=${message}`;
        }

        // Opening the message is the closest thing to proof it was sent.
        try {
          await API.reminders.update(reminder.id, { status: 'SENT' });
          load();
        } catch (err) {
          App.handleError(err);
        }
        return;
      }

      const doneBtn = e.target.closest('[data-done]');
      if (doneBtn) {
        try {
          await API.reminders.update(doneBtn.dataset.done, { status: 'DONE' });
          App.toastSuccess('Reminder closed');
          load();
        } catch (err) {
          App.handleError(err);
        }
        return;
      }

      const reopenBtn = e.target.closest('[data-reopen]');
      if (reopenBtn) {
        try {
          await API.reminders.update(reopenBtn.dataset.reopen, { status: 'PENDING' });
          load();
        } catch (err) {
          App.handleError(err);
        }
        return;
      }

      const deleteBtn = e.target.closest('[data-delete]');
      if (deleteBtn) {
        if (!confirm('Delete this reminder?')) return;
        try {
          await API.reminders.remove(deleteBtn.dataset.delete);
          App.toastSuccess('Reminder deleted');
          load();
        } catch (err) {
          App.handleError(err);
        }
      }
    });
  }

  function init() {
    document.querySelectorAll('[data-lang]').forEach((btn) => {
      btn.addEventListener('click', () => {
        language = btn.dataset.lang;
        document.querySelectorAll('[data-lang]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        updatePreview();
      });
    });

    document.getElementById('statusFilter')?.addEventListener('change', load);

    initNewReminderModal();
    initListActions();
    load();
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page === 'reminders') init();
  });
})();
