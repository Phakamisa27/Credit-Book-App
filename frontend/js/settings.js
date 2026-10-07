// settings.js — the "More" screen: profile, business info, Safe to draw
// settings, password, help. Everything saves through /api/auth/me.

(() => {
  const modals = {};

  function showError(id, message) {
    const el = document.getElementById(id);
    el.textContent = message;
    el.hidden = !message;
  }

  // Puts the user's details everywhere they appear on this page.
  function renderUser(user) {
    App.setText('ownerName', user.fullName || 'Your profile');
    App.setText('ownerEmail', user.email || '');
    document.querySelectorAll('[data-bind="businessName"]').forEach((el) => {
      el.textContent = user.businessName || 'Add your shop name';
    });

    const small = document.getElementById('avatarSmall');
    small.innerHTML = user.profileImage
      ? `<img src="${App.escapeHtml(user.profileImage)}" alt="" />`
      : '👤';

    document.getElementById('fullName').value = user.fullName || '';
    document.getElementById('accountEmail').value = user.email || '';
    document.getElementById('businessName').value = user.businessName || '';
    document.getElementById('businessPhone').value = user.businessPhone || '';
    renderPhoto(user.profileImage);
    renderDrawRules(user);
  }

  // ------------------------------------------------------- safe to draw --
  function renderDrawRules(user) {
    // Older cached users have no settings yet; the server fills them in.
    if (user.bufferPercent === undefined) return;
    const reserve = user.restockReserve;
    App.setText(
      'drawRulesSub',
      `Restock ${reserve === null ? 'not set' : App.formatRands(reserve)} · ` +
        `Buffer ${user.bufferPercent}%`
    );
    document.getElementById('restockReserve').value = reserve === null ? '' : reserve;
    document.getElementById('bufferPercent').value = user.bufferPercent;
  }

  function initDrawRulesForm() {
    const form = document.getElementById('drawRulesForm');
    const money = /^\d+(\.\d{1,2})?$/;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      showError('drawRulesError', '');

      const reserve = form.elements.restockReserve.value.trim();
      const buffer = form.elements.bufferPercent.value.trim();

      if (!money.test(reserve)) {
        return showError('drawRulesError', 'Enter a restock reserve in rand, e.g. 300 (or 0).');
      }
      if (!money.test(buffer) || Number(buffer) > 100) {
        return showError('drawRulesError', 'Enter a buffer from 0 to 100, e.g. 10.');
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const user = await API.auth.updateMe({
            restockReserve: Number(reserve),
            bufferPercent: Number(buffer),
          });
          API.setSession(API.getToken(), user);
          renderUser(user);
          modals.drawRulesModal.close();

          // Show the effect straight away. Home recalculates on its next load.
          try {
            const cash = await API.cash.summary();
            App.toastSuccess(`Saved. Safe to draw is now ${App.formatRands(cash.safeToDraw.amount)}`);
          } catch (_) {
            App.toastSuccess('Saved');
          }
        } catch (err) {
          showError('drawRulesError', err.message);
        }
      });
    });
  }

  function saved(user, message) {
    API.setSession(API.getToken(), user);
    renderUser(user);
    App.toastSuccess(message);
  }

  // ------------------------------------------------------------ profile --
  function initProfileForm() {
    const form = document.getElementById('profileForm');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      showError('profileError', '');

      const fullName = form.elements.fullName.value.trim();
      if (!fullName) return showError('profileError', 'Please enter your name.');

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          saved(await API.auth.updateMe({ fullName }), 'Profile saved');
          modals.profileModal.close();
        } catch (err) {
          showError('profileError', err.message);
        }
      });
    });
  }

  // ----------------------------------------------------------- business --
  function initBusinessForm() {
    const form = document.getElementById('businessForm');
    App.bindPhoneInput(form.elements.businessPhone);

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      showError('businessError', '');

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const user = await API.auth.updateMe({
            businessName: form.elements.businessName.value.trim(),
            businessPhone: form.elements.businessPhone.value.trim(),
          });
          saved(user, 'Business information saved');
          modals.businessModal.close();
        } catch (err) {
          showError('businessError', err.message);
        }
      });
    });
  }

  // -------------------------------------------------------------- photo --
  function renderPhoto(dataUri) {
    const img = document.getElementById('profilePhoto');
    const placeholder = document.getElementById('profilePhotoPlaceholder');
    const removeBtn = document.getElementById('removeProfilePhoto');

    if (dataUri) {
      img.src = dataUri;
      img.hidden = false;
      placeholder.hidden = true;
      removeBtn.hidden = false;
    } else {
      img.removeAttribute('src');
      img.hidden = true;
      placeholder.hidden = false;
      removeBtn.hidden = true;
    }
  }

  function initPhotoUpload() {
    const input = document.getElementById('profilePhotoInput');
    document.getElementById('uploadPhotoBtn').addEventListener('click', () => input.click());

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      input.value = '';
      if (!file) return;
      if (!file.type.startsWith('image/')) return App.toastError('Please choose an image file');
      if (file.size > 2 * 1024 * 1024) {
        return App.toastError('That photo is too large. Please use one under 2MB.');
      }

      const reader = new FileReader();
      reader.onload = async () => {
        try {
          saved(await API.auth.updateMe({ profileImage: reader.result }), 'Photo saved');
        } catch (err) {
          App.handleError(err);
        }
      };
      reader.onerror = () => App.toastError('Could not read that image');
      reader.readAsDataURL(file);
    });

    document.getElementById('removeProfilePhoto').addEventListener('click', async () => {
      try {
        saved(await API.auth.updateMe({ profileImage: '' }), 'Photo removed');
      } catch (err) {
        App.handleError(err);
      }
    });
  }

  // ----------------------------------------------------------- password --
  function initPasswordForm() {
    const form = document.getElementById('passwordForm');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      showError('passwordError', '');

      const currentPassword = form.elements.currentPassword.value;
      const newPassword = form.elements.newPassword.value;
      const confirmPassword = form.elements.confirmPassword.value;

      if (!currentPassword) return showError('passwordError', 'Enter your current password.');
      if (newPassword.length < 8) {
        return showError('passwordError', 'New password must be at least 8 characters.');
      }
      if (newPassword !== confirmPassword) {
        return showError('passwordError', 'New passwords do not match.');
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.auth.changePassword({ currentPassword, newPassword, confirmPassword });
          form.reset();
          App.toastSuccess('Password updated');
        } catch (err) {
          showError('passwordError', err.message);
        }
      });
    });
  }

  // --------------------------------------------------------------- init --
  document.addEventListener('DOMContentLoaded', async () => {
    if (document.body.dataset.page !== 'settings') return;

    ['profileModal', 'businessModal', 'drawRulesModal', 'helpModal', 'aboutModal'].forEach((id) => {
      modals[id] = Modal.create(id);
    });
    document.querySelectorAll('[data-open]').forEach((row) => {
      row.addEventListener('click', () => modals[row.dataset.open].open());
    });
    document.querySelectorAll('[data-chevron]').forEach((el) => {
      el.innerHTML = App.ICONS.chevron;
    });
    document.getElementById('aboutLogo').innerHTML = App.LOGO_SVG.replace(
      'class="tc-logo"',
      'class="tc-logo" style="width:64px;height:64px"'
    );

    // Not built yet. Tapping it still tells us owners want it.
    document.getElementById('notificationsRow').addEventListener('click', () => {
      App.toast('Stock alerts are coming soon.');
    });

    initProfileForm();
    initBusinessForm();
    initPhotoUpload();
    initPasswordForm();
    initDrawRulesForm();

    const cached = API.getCachedUser();
    if (cached) renderUser(cached);
    try {
      renderUser(await API.auth.me());
    } catch (err) {
      App.handleError(err);
    }

    // Home's "Set it" / "Change these amounts" links land here.
    if (window.location.hash === '#safe-to-draw') modals.drawRulesModal.open();
  });
})();
