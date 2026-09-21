// stock.js — the Stock screen: list products, add one, update a count.
//
// The whole list is loaded once; search and the filter chips then work on it
// in the browser, which is instant and fine for a shop's few dozen products.

(() => {
  let products = [];
  let filter = 'ALL';
  let editing = null; // the product open in the form, or null when adding

  let modal;
  let form;
  // The form's inputs by name. Not `form.name`: that is the form's own
  // name attribute, which hides the input called "name".
  let fields;

  // --------------------------------------------------------------- list --
  function visibleProducts() {
    const term = document.getElementById('search').value.trim().toLowerCase();
    return products.filter(
      (p) => (filter === 'ALL' || p.status === filter) && p.name.toLowerCase().includes(term)
    );
  }

  function render() {
    const el = document.getElementById('stockList');
    const rows = visibleProducts();

    if (products.length === 0) {
      el.innerHTML = `<div class="tc-empty">
        <span class="emoji">📦</span>
        <p>No products yet. Add the things you sell most — bread, cooldrinks, airtime…</p>
        <button class="btn btn-primary" type="button" data-add>Add your first product</button>
      </div>`;
      return;
    }
    if (rows.length === 0) {
      el.innerHTML = `<div class="tc-empty"><span class="emoji">🔍</span><p>No products match.</p></div>`;
      return;
    }

    el.innerHTML = rows
      .map(
        (p) => `<button class="tc-row" type="button" data-id="${p.id}">
          <span class="tc-row-icon" aria-hidden="true">${App.itemEmoji(p.name)}</span>
          <span class="tc-row-main">
            <span class="tc-row-title">${App.escapeHtml(p.name)}</span>
            <span class="tc-row-sub">${App.unitsText(p.quantity)}</span>
          </span>
          ${App.stockPill(p)}
          <span class="tc-chevron">${App.ICONS.chevron}</span>
        </button>`
      )
      .join('');
  }

  async function load() {
    try {
      products = await API.items.list();
      // Running low first, then A–Z: the top of the list is what needs buying.
      products.sort((a, b) => {
        if (a.status !== b.status) return a.status === 'LOW' ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      render();
    } catch (err) {
      App.handleError(err);
      App.setHtml('stockList', `<div class="tc-empty"><p>${App.escapeHtml(err.message)}</p></div>`);
    }
  }

  function setFilter(value) {
    filter = value;
    document.querySelectorAll('[data-filter]').forEach((chip) => {
      chip.classList.toggle('active', chip.dataset.filter === value);
    });
    render();
  }

  // --------------------------------------------------------------- form --
  function showError(message) {
    const el = document.getElementById('productError');
    el.textContent = message;
    el.hidden = !message;
  }

  function resetDeleteButton() {
    const btn = document.getElementById('deleteProductBtn');
    btn.textContent = 'Delete product';
    btn.classList.remove('btn-danger');
    btn.classList.add('btn-outline');
    delete btn.dataset.armed;
  }

  function openForm(product) {
    editing = product || null;
    showError('');
    resetDeleteButton();

    fields.name.value = product ? product.name : '';
    fields.price.value = product ? product.price : '';
    fields.quantity.value = product ? product.quantity : 0;
    fields.lowStockLevel.value = product ? product.lowStockLevel : 5;
    fields.reorderQuantity.value = product ? product.reorderQuantity : 10;

    App.setText('productTitle', product ? product.name : 'Add product');
    // A new product needs its name and price, so show those straight away.
    document.getElementById('productDetails').open = !product;
    document.querySelector('#productDetails summary').textContent = product
      ? 'Edit details'
      : 'Product details';
    document.getElementById('deleteProductBtn').hidden = !product;

    modal.open();
    (product ? fields.quantity : fields.name).focus();
  }

  function wholeNumber(value) {
    return /^\d+$/.test(String(value).trim()) ? Number(value) : null;
  }

  function readForm() {
    const name = fields.name.value.trim();
    const price = Number(fields.price.value);
    const quantity = wholeNumber(fields.quantity.value);
    const lowStockLevel = wholeNumber(fields.lowStockLevel.value);
    const reorderQuantity = wholeNumber(fields.reorderQuantity.value);

    const openDetails = (message) => {
      document.getElementById('productDetails').open = true;
      return { error: message };
    };

    if (quantity === null) return { error: 'How many are in the shop? Use a whole number, e.g. 12.' };
    if (!name) return openDetails('Enter the product name.');
    if (!Number.isFinite(price) || price <= 0) return openDetails('Enter the price you pay per unit.');
    if (lowStockLevel === null) return openDetails('"Running low at" must be a whole number.');
    if (reorderQuantity === null || reorderQuantity < 1) {
      return openDetails('"Usually order" must be at least 1.');
    }

    return { data: { name, price, quantity, lowStockLevel, reorderQuantity } };
  }

  async function save(e) {
    e.preventDefault();
    showError('');
    const { data, error } = readForm();
    if (error) return showError(error);

    await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
      try {
        if (editing) {
          await API.items.update(editing.id, data);
          App.toastSuccess(`${data.name}: ${App.unitsText(data.quantity)}`);
        } else {
          await API.items.create(data);
          App.toastSuccess(`${data.name} added`);
        }
        modal.close();
        load();
      } catch (err) {
        // The server's wording comes from the Credit Book ("quick item").
        showError(err.status === 409 ? 'You already have a product with that name.' : err.message);
      }
    });
  }

  // Two taps to delete, instead of a browser confirm() pop-up.
  async function remove() {
    const btn = document.getElementById('deleteProductBtn');
    if (!btn.dataset.armed) {
      btn.dataset.armed = 'yes';
      btn.textContent = 'Tap again to delete';
      btn.classList.replace('btn-outline', 'btn-danger');
      return;
    }
    try {
      await API.items.remove(editing.id);
      App.toastSuccess(`${editing.name} deleted`);
      modal.close();
      load();
    } catch (err) {
      showError(err.message);
    }
  }

  // --------------------------------------------------------------- init --
  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'stock') return;

    modal = Modal.create('productModal');
    form = document.getElementById('productForm');
    fields = form.elements;
    document.getElementById('searchIcon').outerHTML = App.ICONS.search;

    document.getElementById('addProductBtn').addEventListener('click', () => openForm(null));
    document.getElementById('search').addEventListener('input', render);
    document.querySelectorAll('[data-filter]').forEach((chip) => {
      chip.addEventListener('click', () => setFilter(chip.dataset.filter));
    });

    document.getElementById('stockList').addEventListener('click', (e) => {
      if (e.target.closest('[data-add]')) return openForm(null);
      const row = e.target.closest('[data-id]');
      if (row) openForm(products.find((p) => p.id === Number(row.dataset.id)));
    });

    form.querySelectorAll('[data-step]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const current = wholeNumber(fields.quantity.value) || 0;
        fields.quantity.value = Math.max(0, current + Number(btn.dataset.step));
      });
    });

    form.addEventListener('submit', save);
    document.getElementById('deleteProductBtn').addEventListener('click', remove);

    // Links from Home: stock.html?filter=low and stock.html?add=1
    if (App.getParam('filter') === 'low') setFilter('LOW');
    if (App.getParam('add')) openForm(null);

    load();
  });
})();
