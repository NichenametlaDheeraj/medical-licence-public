/**
 * excel_sync.js — Smart In-Place Excel Export & Synchronization
 * 
 * First click: Downloads and links the Excel file via File System Access API.
 * Next clicks: Directly updates the already downloaded file on disk without
 * triggering duplicate browser downloads.
 * Works seamlessly for both Staff Users ('My Data') and Admins ('All Data').
 */

(function () {
  'use strict';

  // ── IndexedDB Storage for File Handles ───────────────────────────────────
  const DB_NAME = 'MedLicenceExcelSyncDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'handles';

  const ExcelDB = {
    _db: null,

    async getDB() {
      if (this._db) return this._db;
      return new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, DB_VERSION);
        req.onupgradeneeded = (e) => {
          const db = e.target.result;
          if (!db.objectStoreNames.contains(STORE_NAME)) {
            db.createObjectStore(STORE_NAME);
          }
        };
        req.onsuccess = () => {
          this._db = req.result;
          resolve(this._db);
        };
        req.onerror = () => reject(req.error);
      });
    },

    async get(key) {
      try {
        const db = await this.getDB();
        return new Promise((resolve) => {
          const tx = db.transaction(STORE_NAME, 'readonly');
          const req = tx.objectStore(STORE_NAME).get(key);
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => resolve(null);
        });
      } catch (e) {
        console.warn('ExcelDB get error:', e);
        return null;
      }
    },

    async set(key, value) {
      try {
        const db = await this.getDB();
        return new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const req = tx.objectStore(STORE_NAME).put(value, key);
          req.onsuccess = () => resolve();
          req.onerror = () => reject(req.error);
        });
      } catch (e) {
        console.warn('ExcelDB set error:', e);
      }
    },

    async delete(key) {
      try {
        const db = await this.getDB();
        return new Promise((resolve) => {
          const tx = db.transaction(STORE_NAME, 'readwrite');
          const req = tx.objectStore(STORE_NAME).delete(key);
          req.onsuccess = () => resolve();
          req.onerror = () => resolve();
        });
      } catch (e) {
        console.warn('ExcelDB delete error:', e);
      }
    }
  };

  // ── Toast / Flash Notification Helper ────────────────────────────────────
  function showToast(category, message, autoDismiss = 6000) {
    let container = document.querySelector('.flash-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'flash-container position-fixed top-0 end-0 p-3';
      container.style.zIndex = '99999';
      document.body.appendChild(container);
    }

    const alertEl = document.createElement('div');
    alertEl.className = `alert alert-${category} alert-dismissible fade show shadow-sm mb-2`;
    alertEl.setAttribute('role', 'alert');
    alertEl.style.minWidth = '320px';
    alertEl.innerHTML = `
      <div class="d-flex align-items-center gap-2">
        <i class="bi ${category === 'success' ? 'bi-check-circle-fill' : category === 'warning' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'}"></i>
        <div>${message}</div>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    container.appendChild(alertEl);

    if (autoDismiss > 0) {
      setTimeout(() => {
        try {
          if (window.bootstrap && bootstrap.Alert) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (bsAlert) bsAlert.close();
          } else {
            alertEl.remove();
          }
        } catch (_) {
          alertEl.remove();
        }
      }, autoDismiss);
    }
  }

  // ── UI Updates Based on Download / Link State ────────────────────────────
  async function refreshExportButtons() {
    const isSupported = ('showSaveFilePicker' in window);
    const syncButtons = document.querySelectorAll('.btn-excel-sync');
    if (!syncButtons.length) return;

    for (const btn of syncButtons) {
      const exportType = btn.dataset.exportType || 'all';
      const userId = btn.dataset.userId || 'current';
      const userRole = btn.dataset.userRole || 'staff';
      const appId = btn.dataset.appId;
      const key = (exportType === 'single') ? `excel_sync_app_${appId}` : `excel_sync_user_${userId}`;

      if (isSupported) {
        const handle = await ExcelDB.get(key);
        if (handle) {
          btn.dataset.hasDownloaded = 'true';
          btn.dataset.filename = handle.name || '';

          // Update sidebar link
          const navText = btn.querySelector('.excel-nav-text');
          const badge = btn.querySelector('.excel-linked-badge');
          if (navText) {
            navText.textContent = (userRole === 'admin') ? 'Update All (Excel)' : 'Update My Data (Excel)';
          }
          if (badge) {
            badge.classList.remove('d-none');
            badge.textContent = 'Linked';
            badge.title = `Linked to ${handle.name}. Click to update existing file.`;
          }

          // Update dashboard button
          const dashText = btn.querySelector('.excel-dash-text');
          if (dashText) {
            const icon = btn.querySelector('i');
            if (icon) {
              icon.className = 'bi bi-arrow-repeat';
            }
            dashText.textContent = (userRole === 'admin') ? 'Update All' : 'Update Mine';
            btn.classList.remove('btn-outline-success');
            btn.classList.add('btn-success');
          }

          // Update generic button
          if (!navText && !dashText && !btn.querySelector('i:only-child')) {
            btn.innerHTML = `<i class="bi bi-arrow-repeat"></i> Update Excel (${handle.name})`;
          }
          btn.setAttribute('title', `File '${handle.name}' already downloaded. Click to update in-place without duplicate download. (Hold Shift to Save As new copy)`);
        }
      }
    }
  }

  // ── Core Export & Sync Logic ─────────────────────────────────────────────
  async function handleExcelExport(e) {
    const btn = e.currentTarget;
    const url = btn.getAttribute('href');
    if (!url || url === '#') return;

    // Check if File System Access API is supported
    const isSupported = ('showSaveFilePicker' in window);
    if (!isSupported) {
      // Browser does not support direct file write (e.g. Firefox)
      // Allow default browser download navigation
      return;
    }

    // Intercept click to perform in-place sync
    e.preventDefault();
    e.stopPropagation();

    const exportType = btn.dataset.exportType || 'all';
    const userId = btn.dataset.userId || 'current';
    const userRole = btn.dataset.userRole || 'staff';
    const appId = btn.dataset.appId;
    const appNumber = btn.dataset.appNumber;
    const key = (exportType === 'single') ? `excel_sync_app_${appId}` : `excel_sync_user_${userId}`;

    // Determine default suggested filename
    let defaultFilename = (userRole === 'admin') ? 'all_applications.xlsx' : 'my_applications.xlsx';
    if (exportType === 'single') {
      defaultFilename = appNumber ? `application_${appNumber}.xlsx` : `application_${appId}.xlsx`;
    }

    // If user holds Shift, force Save As new file
    const forceNewFile = e.shiftKey;

    // Visual button state: show loading spinner
    const originalHTML = btn.innerHTML;
    btn.style.pointerEvents = 'none';
    const iconEl = btn.querySelector('i');
    if (iconEl) {
      iconEl.className = 'spinner-border spinner-border-sm me-1';
    }

    try {
      let handle = forceNewFile ? null : await ExcelDB.get(key);

      if (handle) {
        // ── SCENARIO A: Already downloaded! Update in place ───────────────
        let perm = await handle.queryPermission({ mode: 'readwrite' });
        if (perm === 'prompt') {
          perm = await handle.requestPermission({ mode: 'readwrite' });
        }

        if (perm !== 'granted') {
          showToast('warning', `Permission to update '${handle.name}' was not granted. Please select where to save.`);
          await ExcelDB.delete(key);
          handle = null;
        }
      }

      if (handle) {
        // Fetch fresh Excel binary from server
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        if (!res.ok) {
          throw new Error(`Export failed on server with status ${res.status}`);
        }
        const blob = await res.blob();

        try {
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();

          showToast(
            'success',
            `<strong>✓ Excel Updated!</strong> Already downloaded file <code>${handle.name}</code> was updated in-place with latest data.<br><small class="text-muted">No duplicate file was downloaded. (Hold Shift to Save As new copy)</small>`,
            7000
          );
          await refreshExportButtons();
          return;
        } catch (writeErr) {
          const errMsg = writeErr.message || '';
          if (
            writeErr.name === 'NoModificationAllowedError' ||
            errMsg.toLowerCase().includes('in use') ||
            errMsg.toLowerCase().includes('process')
          ) {
            showToast(
              'warning',
              `<strong>⚠️ File In Use:</strong> The Excel file <code>${handle.name}</code> is currently open in Microsoft Excel. Please close it in Excel first, then click Update again.`,
              9000
            );
            return;
          } else {
            console.warn('File write failed, resetting handle:', writeErr);
            await ExcelDB.delete(key);
            handle = null; // Re-prompt save picker
          }
        }
      }

      // ── SCENARIO B: First time download or re-linking ─────────────────────
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Export failed on server with status ${res.status}`);
      }
      const blob = await res.blob();

      try {
        handle = await window.showSaveFilePicker({
          suggestedName: defaultFilename,
          types: [{
            description: 'Excel Spreadsheet (*.xlsx)',
            accept: {
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
            }
          }]
        });
      } catch (pickerErr) {
        // User cancelled the file picker dialog
        return;
      }

      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();

      // Store file handle in IndexedDB
      await ExcelDB.set(key, handle);

      showToast(
        'success',
        `<strong>✓ File Saved & Linked!</strong> Saved to <code>${handle.name}</code>.<br><small class="text-muted">Next time you click, this existing file will be updated directly without downloading duplicates.</small>`,
        8000
      );
      await refreshExportButtons();

    } catch (err) {
      console.error('Excel Export Error:', err);
      showToast('danger', `Export failed: ${err.message || 'Unknown error'}`);
    } finally {
      btn.style.pointerEvents = '';
      btn.innerHTML = originalHTML;
      await refreshExportButtons();
    }
  }

  // ── Initialize on DOM Ready ──────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Attach click listener to all excel sync buttons
    document.querySelectorAll('.btn-excel-sync').forEach(function (btn) {
      btn.addEventListener('click', handleExcelExport);
    });

    // Also auto-bind any link pointing to /exports/all or /exports/application/
    document.querySelectorAll('a[href*="/exports/"]').forEach(function (a) {
      if (!a.classList.contains('btn-excel-sync')) {
        a.classList.add('btn-excel-sync');
        if (a.getAttribute('href').includes('/exports/all')) {
          a.dataset.exportType = 'all';
        } else {
          a.dataset.exportType = 'single';
        }
        a.addEventListener('click', handleExcelExport);
      }
    });

    // Initial button state check
    refreshExportButtons();
  });

})();
