// settings.js — business profile, profile photo, and password change.

(() => {
  function initProfileForm() {
    const form = document.getElementById('profileForm');
    if (!form) return;

    const errorEl = document.getElementById('profileError');
    App.bindPhoneInput(form.businessPhone);

    async function load() {
      try {
        const user = await API.auth.me();
        form.fullName.value = user.fullName || '';
        form.businessName.value = user.businessName || '';
        form.businessPhone.value = user.businessPhone || '';
        App.setText('accountEmail', user.email);
        App.setText('accountCreated', App.formatDateTime(user.createdAt));
        renderPhoto(user.profileImage);
      } catch (err) {
        App.handleError(err);
      }
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      const fullName = form.fullName.value.trim();
      if (!fullName) {
        errorEl.textContent = 'Please enter your name.';
        errorEl.hidden = false;
        return;
      }

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          const user = await API.auth.updateMe({
            fullName,
            businessName: form.businessName.value.trim(),
            businessPhone: form.businessPhone.value.trim(),
          });
          API.setSession(API.getToken(), user);
          App.toastSuccess('Profile saved');
          document.querySelectorAll('[data-bind="businessName"]').forEach((el) => {
            el.textContent = user.businessName || 'Credit Book';
          });
          // The sidebar caches the business name, so refresh it too.
          const brand = document.querySelector('.side-brand-text strong');
          if (brand) brand.textContent = user.businessName || 'Credit Book';
        } catch (err) {
          errorEl.textContent = err.message;
          errorEl.hidden = false;
        }
      });
    });

    load();
  }

  function renderPhoto(dataUri) {
    const img = document.getElementById('profilePhoto');
    const placeholder = document.getElementById('profilePhotoPlaceholder');
    const removeBtn = document.getElementById('removeProfilePhoto');
    if (!img || !placeholder) return;

    if (dataUri) {
      img.src = dataUri;
      img.hidden = false;
      placeholder.hidden = true;
      if (removeBtn) removeBtn.hidden = false;
    } else {
      img.removeAttribute('src');
      img.hidden = true;
      placeholder.hidden = false;
      if (removeBtn) removeBtn.hidden = true;
    }
  }

  function initPhotoUpload() {
    const input = document.getElementById('profilePhotoInput');
    if (!input) return;

    document.getElementById('uploadPhotoBtn')?.addEventListener('click', () => input.click());

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        App.toastError('Please choose an image file');
        input.value = '';
        return;
      }
      if (file.size > 2 * 1024 * 1024) {
        App.toastError('That photo is too large. Please use one under 2MB.');
        input.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const user = await API.auth.updateMe({ profileImage: reader.result });
          API.setSession(API.getToken(), user);
          renderPhoto(user.profileImage);
          App.toastSuccess('Photo saved');
        } catch (err) {
          App.handleError(err);
        }
      };
      reader.onerror = () => App.toastError('Could not read that image');
      reader.readAsDataURL(file);
      input.value = '';
    });

    document.getElementById('removeProfilePhoto')?.addEventListener('click', async () => {
      try {
        const user = await API.auth.updateMe({ profileImage: '' });
        API.setSession(API.getToken(), user);
        renderPhoto('');
        App.toastSuccess('Photo removed');
      } catch (err) {
        App.handleError(err);
      }
    });
  }

  function initPasswordForm() {
    const form = document.getElementById('passwordForm');
    if (!form) return;

    const errorEl = document.getElementById('passwordError');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorEl.hidden = true;

      function fail(message) {
        errorEl.textContent = message;
        errorEl.hidden = false;
      }

      const currentPassword = form.currentPassword.value;
      const newPassword = form.newPassword.value;
      const confirmPassword = form.confirmPassword.value;

      if (!currentPassword) return fail('Enter your current password.');
      if (newPassword.length < 8) return fail('New password must be at least 8 characters.');
      if (newPassword !== confirmPassword) return fail('New passwords do not match.');

      await App.withBusy(form.querySelector('button[type="submit"]'), async () => {
        try {
          await API.auth.changePassword({ currentPassword, newPassword, confirmPassword });
          form.reset();
          App.toastSuccess('Password updated');
        } catch (err) {
          fail(err.message);
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (document.body.dataset.page !== 'settings') return;
    initProfileForm();
    initPhotoUpload();
    initPasswordForm();
  });
})();
