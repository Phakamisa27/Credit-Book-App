// modal.js — a tiny dialog helper shared by every page that has one.
//
// Expects markup shaped like:
//   <div class="modal" id="x" hidden>
//     <div class="modal-backdrop" data-close></div>
//     <div class="modal-card">… <button data-close>×</button> …</div>
//   </div>

const Modal = (() => {
  function create(id) {
    const el = document.getElementById(id);
    if (!el) {
      // Returning no-ops keeps callers free of null checks on pages where a
      // particular modal does not exist.
      return { open() {}, close() {}, el: null };
    }

    function close() {
      el.hidden = true;
      document.body.style.overflow = '';
    }

    function open() {
      el.hidden = false;
      document.body.style.overflow = 'hidden';
      // Focus the first field so the owner can start typing straight away.
      el.querySelector('input:not([type="hidden"]), select, textarea')?.focus();
    }

    el.querySelectorAll('[data-close]').forEach((btn) => {
      btn.addEventListener('click', close);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !el.hidden) close();
    });

    return { open, close, el };
  }

  return { create };
})();
