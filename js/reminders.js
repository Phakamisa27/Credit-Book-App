// reminders.js — build friendly reminder messages and open WhatsApp/SMS

const Reminders = (() => {
  let channel = 'whatsapp';
  let lang = 'en';
  let customer = null;

  const templates = {
    en: (name, balance, shop) =>
      `Hi ${name}, you have an outstanding balance of ${App.formatCurrency(balance)} at ${shop}. Please settle when you can. Thank you!`,
    zu: (name, balance, shop) =>
      `Sawubona ${name}, unesikweletu esingaka ${App.formatCurrency(balance)} kwa-${shop}. Sicela ukhokhe uma usukwazi. Ngiyabonga!`,
  };

  function init() {
    const root = document.getElementById('remindersRoot');
    if (!root) return;

    const select = document.getElementById('reminderCustomer');
    const customers = Storage.getCustomers();
    if (customers.length === 0) {
      root.innerHTML = `<div class="empty"><span class="emoji">👤</span>
        No customers yet. <a href="add-customer.html">Add a customer</a> first.</div>`;
      return;
    }

    select.innerHTML = customers
      .map((c) => `<option value="${c.id}">${App.escapeHtml(c.name)}</option>`)
      .join('');

    const preselect = App.getParam('id');
    if (preselect && customers.some((c) => c.id === preselect)) select.value = preselect;

    customer = Storage.getCustomer(select.value) || customers[0];
    select.addEventListener('change', () => {
      customer = Storage.getCustomer(select.value);
      updatePreview();
    });

    document.querySelectorAll('[data-channel]').forEach((card) => {
      card.addEventListener('click', () => {
        channel = card.dataset.channel;
        document.querySelectorAll('[data-channel]').forEach((c) => c.classList.remove('selected'));
        card.classList.add('selected');
      });
    });

    document.querySelectorAll('[data-lang]').forEach((btn) => {
      btn.addEventListener('click', () => {
        lang = btn.dataset.lang;
        document.querySelectorAll('[data-lang]').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        updatePreview();
      });
    });

    App.setText('lastSynced', `Last synced: Today, ${new Date().toTimeString().slice(0, 5)}`);
    document.getElementById('syncBtn')?.addEventListener('click', () => {
      Storage.saveSettings({ lastSynced: new Date().toISOString() });
      App.setText('lastSynced', `Last synced: Today, ${new Date().toTimeString().slice(0, 5)}`);
      App.toast('All data synced');
    });

    document.getElementById('sendBtn')?.addEventListener('click', send);

    updatePreview();
  }

  function firstName() {
    return (customer.name || '').split(' ')[0];
  }

  function customerBalance() {
    return Math.max(0, customer.balance || 0);
  }

  function shopName() {
    return Storage.getBusinessProfile().businessName || 'our shop';
  }

  function buildMessage() {
    if (!customer) return '';
    return templates[lang](firstName(), customerBalance(), shopName());
  }

  function updatePreview() {
    const body = document.getElementById('previewBody');
    if (!body || !customer) return;
    const shop = shopName();
    const en = templates.en(firstName(), customerBalance(), shop);
    const zu = templates.zu(firstName(), customerBalance(), shop);
    App.setText('previewPhone', customer.phone ? `📞 ${customer.phone}` : 'No phone number on file');
    body.innerHTML = `<p>${lang === 'en' ? en : zu}</p>
      <p class="muted" style="font-size:0.85rem;">${lang === 'en' ? zu : en}</p>`;
  }

  function send() {
    if (!customer) return;
    const msg = buildMessage();
    const phone = (customer.phone || '').replace(/\D/g, '');
    if (!phone) return App.toast('This customer has no phone number');

    let intl = phone;
    if (intl.startsWith('0')) intl = '27' + intl.slice(1); // South Africa

    if (channel === 'whatsapp') {
      window.open(`https://wa.me/${intl}?text=${encodeURIComponent(msg)}`, '_blank');
    } else {
      window.location.href = `sms:${customer.phone}?body=${encodeURIComponent(msg)}`;
    }
    App.toast('Opening reminder…');
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page === 'reminders') init();
  });

  return {};
})();
