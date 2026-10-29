/* MedLicence — Main JavaScript */

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar Drawer Open / Close ──────────────────────────────────────────
  const toggle   = document.getElementById('sidebarToggle');
  const sidebar  = document.getElementById('sidebar');
  const closeBtn = document.getElementById('sidebarCloseBtn');
  const overlay  = document.getElementById('sidebarOverlay');

  function openSidebar() {
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
  }

  if (toggle) {
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      if (sidebar && sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      closeSidebar();
    });
  }

  if (overlay) {
    overlay.addEventListener('click', function () {
      closeSidebar();
    });
  }

  // Close sidebar when clicking outside or pressing Escape
  document.addEventListener('click', function (e) {
    if (sidebar && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && (!toggle || !toggle.contains(e.target))) {
        closeSidebar();
      }
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
      closeSidebar();
    }
  });

  // ── Auto-dismiss alerts ─────────────────────────────────────────────────
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success').forEach(function (el) {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    });
  }, 5000);

  // ── Table row click → navigate ──────────────────────────────────────────
  document.querySelectorAll('tr[data-href]').forEach(function (row) {
    row.style.cursor = 'pointer';
    row.addEventListener('click', function (e) {
      if (!e.target.closest('a, button, form')) {
        window.location.href = row.dataset.href;
      }
    });
  });

  // ── Confirm dangerous actions ───────────────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(el.dataset.confirm)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  // ── Tooltips ────────────────────────────────────────────────────────────
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(function (el) {
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });

  // ── Form field — copy business address to shop address ──────────────────
  const copyAddrBtn = document.getElementById('copyBusinessAddr');
  if (copyAddrBtn) {
    copyAddrBtn.addEventListener('click', function () {
      const src  = document.querySelector('[name="full_address"]');
      const dest = document.querySelector('[name="shop_address"]');
      if (src && dest) {
        dest.value = src.value;
        ['shop_district', 'shop_state', 'shop_pincode', 'shop_mandal', 'shop_village'].forEach(function (f) {
          const srcF = document.querySelector('[name="' + f.replace('shop_', '') + '"]');
          const dstF = document.querySelector('[name="' + f + '"]');
          if (srcF && dstF) dstF.value = srcF.value;
        });
      }
    });
  }

  // ── PIN Code auto-format ─────────────────────────────────────────────────
  document.querySelectorAll('input[name="pincode"], input[name="shop_pincode"]').forEach(function (el) {
    el.addEventListener('input', function () {
      this.value = this.value.replace(/\D/g, '').slice(0, 6);
    });
  });

  // ── Mobile number auto-format ────────────────────────────────────────────
  document.querySelectorAll('input[type="tel"]').forEach(function (el) {
    el.addEventListener('input', function () {
      this.value = this.value.replace(/[^\d+\-\s]/g, '').slice(0, 15);
    });
  });

  // ── PAN uppercase ────────────────────────────────────────────────────────
  document.querySelectorAll('input[name="pan"], input[name="proprietor_pan"]').forEach(function (el) {
    el.addEventListener('input', function () {
      this.value = this.value.toUpperCase();
    });
  });

  // ── Generate full address from parts ────────────────────────────────────
  const addrFields = ['door_number', 'floor', 'street', 'village', 'mandal', 'district', 'state', 'pincode'];
  addrFields.forEach(function (f) {
    const el = document.querySelector('[name="' + f + '"]');
    if (el) el.addEventListener('blur', autoFillAddress);
  });

  function autoFillAddress() {
    const fullAddrEl = document.querySelector('[name="full_address"]');
    if (!fullAddrEl || fullAddrEl.value.trim()) return; // Don't overwrite manual input
    const parts = addrFields.map(function (f) {
      const el = document.querySelector('[name="' + f + '"]');
      return el ? el.value.trim() : '';
    }).filter(Boolean);
    fullAddrEl.value = parts.join(', ');
  }

  // ── Print button ─────────────────────────────────────────────────────────
  document.querySelectorAll('.btn-print').forEach(function (btn) {
    btn.addEventListener('click', function () {
      window.print();
    });
  });

  // ── Auto-format UTC timestamps to user's exact local browser time ──────────
  document.querySelectorAll('.user-local-time[data-utc]').forEach(function (el) {
    const utcStr = el.dataset.utc;
    if (utcStr) {
      try {
        const d = new Date(utcStr);
        if (!isNaN(d.getTime())) {
          el.textContent = d.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
          }) + ' ' + d.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
          });
        }
      } catch (err) {
        console.warn('Local time formatting error:', err);
      }
    }
  });

});

// ── Global: format currency ───────────────────────────────────────────────
function formatINR(amount) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);
}

// ── Global: Password Visibility Toggle (Eye Icon) ─────────────────────────
function togglePasswordVisibility(targetId, btn) {
  const input = document.getElementById(targetId);
  if (!input) return;
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  const icon = btn.querySelector('i');
  if (icon) {
    if (isPassword) {
      icon.classList.remove('bi-eye');
      icon.classList.add('bi-eye-slash');
      btn.setAttribute('title', 'Hide password');
    } else {
      icon.classList.remove('bi-eye-slash');
      icon.classList.add('bi-eye');
      btn.setAttribute('title', 'Show password');
    }
  }
}
