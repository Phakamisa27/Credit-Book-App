// storage.js — localStorage data layer for Credit Book
// Frontend-only temporary database. No backend.
//
// Data structures:
// businessProfile = { businessName, ownerName, phone, profileImage, createdAt }
// customers = [{ id, name, phone, gender, area, notes, balance, createdAt }]
// transactions = [{ id, customerId, type ("credit"|"payment"), itemName, amount, dueDate, signature, productPhoto, createdAt }]

const Storage = (() => {
  const KEYS = {
    businessProfile: 'businessProfile',
    customers: 'customers',
    transactions: 'transactions',
    items: 'items',
    settings: 'sc_settings',
  };

  function read(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      console.error('Storage read error', e);
      return fallback;
    }
  }

  function write(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function uid(prefix = 'id') {
    return `${prefix}_${Date.now().toString(36)}_${Math.random()
      .toString(36)
      .slice(2, 7)}`;
  }

  // ---------- Customers ----------
  function getCustomers() {
    return read(KEYS.customers, []);
  }

  function getCustomer(id) {
    return getCustomers().find((c) => c.id === id) || null;
  }

  function saveCustomer({ name, phone, gender, area, notes }) {
    const customers = getCustomers();
    const customer = {
      id: uid('cus'),
      name: (name || '').trim(),
      phone: (phone || '').trim(),
      gender: gender === 'female' ? 'female' : gender === 'male' ? 'male' : '',
      area: (area || '').trim(),
      notes: (notes || '').trim(),
      balance: 0,
      createdAt: new Date().toISOString(),
    };
    customers.push(customer);
    write(KEYS.customers, customers);
    return customer;
  }

  function updateCustomer(id, patch) {
    const customers = getCustomers();
    const idx = customers.findIndex((c) => c.id === id);
    if (idx === -1) return null;
    customers[idx] = { ...customers[idx], ...patch };
    write(KEYS.customers, customers);
    return customers[idx];
  }

  function setBalance(id, balance) {
    return updateCustomer(id, { balance: Math.round(balance * 100) / 100 });
  }

  function deleteCustomer(id) {
    write(KEYS.customers, getCustomers().filter((c) => c.id !== id));
    write(KEYS.transactions, getTransactions().filter((t) => t.customerId !== id));
  }

  // ---------- Transactions ----------
  function getTransactions() {
    return read(KEYS.transactions, []);
  }

  function getCustomerTransactions(customerId) {
    return getTransactions()
      .filter((t) => t.customerId === customerId)
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  }

  // Adds a transaction AND updates the customer's stored balance.
  // credit -> balance increases, payment -> balance decreases.
  function addTransaction({ customerId, type, itemName, amount, dueDate, signature, productPhoto }) {
    const transactions = getTransactions();
    const tx = {
      id: uid('tx'),
      customerId,
      type, // "credit" | "payment"
      itemName: (itemName || (type === 'payment' ? 'Payment' : 'Item')).trim(),
      amount: Math.round(Number(amount) * 100) / 100,
      dueDate: type === 'credit' && dueDate ? dueDate : null,
      signature: signature || '',
      productPhoto: productPhoto || '',
      createdAt: new Date().toISOString(),
    };
    transactions.push(tx);
    write(KEYS.transactions, transactions);

    const customer = getCustomer(customerId);
    if (customer) {
      const delta = type === 'credit' ? tx.amount : -tx.amount;
      setBalance(customerId, (customer.balance || 0) + delta);
    }
    return tx;
  }

  function deleteTransaction(id) {
    write(KEYS.transactions, getTransactions().filter((t) => t.id !== id));
    recomputeBalances();
  }

  // Recalculate every customer's balance from the transaction log.
  function recomputeBalances() {
    const txs = getTransactions();
    const customers = getCustomers().map((c) => {
      const balance = txs
        .filter((t) => t.customerId === c.id)
        .reduce((bal, t) => (t.type === 'credit' ? bal + t.amount : bal - t.amount), 0);
      return { ...c, balance: Math.round(balance * 100) / 100 };
    });
    write(KEYS.customers, customers);
  }

  // ---------- Items / Products (owner-defined quick items) ----------
  function getItems() {
    return read(KEYS.items, []);
  }

  function addItem({ name, price }) {
    const items = getItems();
    const item = {
      id: uid('item'),
      name: (name || '').trim(),
      price: Math.round(Number(price) * 100) / 100,
      createdAt: new Date().toISOString(),
    };
    items.push(item);
    write(KEYS.items, items);
    return item;
  }

  function deleteItem(id) {
    write(KEYS.items, getItems().filter((i) => i.id !== id));
  }

  // ---------- Derived dashboard data ----------
  function getBalance(customerId) {
    const c = getCustomer(customerId);
    return c ? c.balance || 0 : 0;
  }

  function getTotalOutstanding() {
    return getCustomers().reduce((sum, c) => sum + Math.max(0, c.balance || 0), 0);
  }

  function isToday(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    return (
      d.getFullYear() === now.getFullYear() &&
      d.getMonth() === now.getMonth() &&
      d.getDate() === now.getDate()
    );
  }

  function getTodayCredit() {
    return getTransactions()
      .filter((t) => t.type === 'credit' && isToday(t.createdAt))
      .reduce((s, t) => s + t.amount, 0);
  }

  function getTodayPayments() {
    return getTransactions()
      .filter((t) => t.type === 'payment' && isToday(t.createdAt))
      .reduce((s, t) => s + t.amount, 0);
  }

  // ---------- Due date tracking ----------
  function getTodayDateOnly() {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, '0');
    const d = String(now.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  function getDueStatus(dueDate, balance) {
    if (!dueDate) return null;
    if ((balance || 0) <= 0) return 'Paid';
    const today = getTodayDateOnly();
    if (dueDate > today) return 'Not Due';
    if (dueDate === today) return 'Due Today';
    return 'Overdue';
  }

  const DUE_STATUS_PRIORITY = { Overdue: 3, 'Due Today': 2, 'Not Due': 1 };

  function getCustomerDueInfo(customer) {
    const balance = customer.balance || 0;
    if (balance <= 0) return { dueDate: null, status: 'Paid' };

    const credits = getCustomerTransactions(customer.id).filter(
      (t) => t.type === 'credit' && t.dueDate
    );
    if (credits.length === 0) return { dueDate: null, status: null };

    let best = null;
    for (const tx of credits) {
      const status = getDueStatus(tx.dueDate, balance);
      if (!status || status === 'Paid') continue;
      if (
        !best ||
        DUE_STATUS_PRIORITY[status] > DUE_STATUS_PRIORITY[best.status] ||
        (DUE_STATUS_PRIORITY[status] === DUE_STATUS_PRIORITY[best.status] &&
          tx.dueDate < best.dueDate)
      ) {
        best = { dueDate: tx.dueDate, status };
      }
    }
    return best || { dueDate: null, status: null };
  }

  function getCustomerCreditTotals(customerId) {
    const txs = getCustomerTransactions(customerId);
    const totalCredit = txs
      .filter((t) => t.type === 'credit')
      .reduce((s, t) => s + t.amount, 0);
    const totalPaid = txs
      .filter((t) => t.type === 'payment')
      .reduce((s, t) => s + t.amount, 0);
    return { totalCredit, totalPaid };
  }

  function getDueTodayCount() {
    return getCustomers().filter((c) => {
      const info = getCustomerDueInfo(c);
      return info.status === 'Due Today';
    }).length;
  }

  function getOverdueCount() {
    return getCustomers().filter((c) => {
      const info = getCustomerDueInfo(c);
      return info.status === 'Overdue';
    }).length;
  }

  // ---------- Business profile ----------
  // Returns a profile object. When nothing is stored yet, all fields are empty
  // so callers can simply check `profile.businessName`.
  function getBusinessProfile() {
    return read(KEYS.businessProfile, {
      businessName: '',
      ownerName: '',
      phone: '',
      profileImage: '',
      createdAt: '',
    });
  }

  function hasBusinessProfile() {
    return !!getBusinessProfile().businessName;
  }

  function saveBusinessProfile({ businessName, ownerName, phone }) {
    const existing = getBusinessProfile();
    const profile = {
      businessName: (businessName || '').trim(),
      ownerName: (ownerName || '').trim(),
      phone: (phone || '').trim(),
      profileImage: existing.profileImage || '',
      createdAt: existing.createdAt || new Date().toISOString(),
    };
    write(KEYS.businessProfile, profile);
    return profile;
  }

  function saveProfileImage(profileImage) {
    const existing = getBusinessProfile();
    const profile = {
      ...existing,
      profileImage: profileImage || '',
      createdAt: existing.createdAt || new Date().toISOString(),
    };
    write(KEYS.businessProfile, profile);
    return profile;
  }

  // ---------- Settings (sync metadata only — no hard-coded names) ----------
  function getSettings() {
    return read(KEYS.settings, { lastSynced: new Date().toISOString() });
  }

  function saveSettings(patch) {
    const next = { ...getSettings(), ...patch };
    write(KEYS.settings, next);
    return next;
  }

  // ---------- API sync cache (keeps transactions/credit pages working) ----------
  function syncBusinessProfileFromApi(profile) {
    if (profile) {
      write(KEYS.businessProfile, profile);
    } else {
      localStorage.removeItem(KEYS.businessProfile);
    }
  }

  function syncCustomersFromApi(customers) {
    write(KEYS.customers, customers);
  }

  function syncCustomerFromApi(customer) {
    const list = getCustomers();
    const idx = list.findIndex((c) => c.id === customer.id);
    if (idx === -1) list.push(customer);
    else list[idx] = { ...list[idx], ...customer };
    write(KEYS.customers, list);
  }

  return {
    KEYS,
    getBusinessProfile,
    hasBusinessProfile,
    saveBusinessProfile,
    saveProfileImage,
    getCustomers,
    getCustomer,
    saveCustomer,
    updateCustomer,
    setBalance,
    deleteCustomer,
    getTransactions,
    getCustomerTransactions,
    addTransaction,
    deleteTransaction,
    recomputeBalances,
    getItems,
    addItem,
    deleteItem,
    getBalance,
    getTotalOutstanding,
    getTodayCredit,
    getTodayPayments,
    getTodayDateOnly,
    getDueStatus,
    getCustomerDueInfo,
    getCustomerCreditTotals,
    getDueTodayCount,
    getOverdueCount,
    getSettings,
    saveSettings,
    syncBusinessProfileFromApi,
    syncCustomersFromApi,
    syncCustomerFromApi,
  };
})();
