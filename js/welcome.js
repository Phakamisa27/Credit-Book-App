// welcome.js — landing page (index.html)

document.addEventListener('DOMContentLoaded', () => {
  const hasProfile = Storage.hasBusinessProfile();
  const primaryBtn = document.getElementById('primaryBtn');
  const secondaryBtn = document.getElementById('secondaryBtn');
  const returningBlock = document.getElementById('returningBlock');

  if (hasProfile) {
    const profile = Storage.getBusinessProfile();
    if (returningBlock) {
      returningBlock.hidden = false;
      const nameEl = document.getElementById('returningName');
      if (nameEl) nameEl.textContent = profile.businessName;
    }
    if (primaryBtn) {
      primaryBtn.textContent = 'Go to Dashboard';
      primaryBtn.href = 'dashboard.html';
    }
    if (secondaryBtn) secondaryBtn.hidden = true;
  } else {
    if (primaryBtn) {
      primaryBtn.textContent = 'Get Started';
      primaryBtn.href = 'dashboard.html';
    }
    if (secondaryBtn) secondaryBtn.hidden = false;
  }
});
