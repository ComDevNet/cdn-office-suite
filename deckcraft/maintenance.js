(() => {
  const app = location.pathname.split('/')[1];
  const names = {deckcraft:'Deckcraft', wordcraft:'Wordcraft', gridcraft:'Gridcraft', pdfcraft:'PDFcraft', vectorcraft:'Vectorcraft', cadcraft:'CADcraft', photocraft:'Photocraft'};
  const name = names[app] || 'This app';
  const dialog = document.createElement('dialog');
  dialog.setAttribute('aria-labelledby', 'cdn-maintenance-title');
  dialog.style.cssText = 'border:0;border-radius:20px;padding:32px;max-width:480px;width:calc(100% - 40px);font:16px/1.5 system-ui;color:#232323;background:#fff;box-shadow:0 16px 80px #0005';
  dialog.innerHTML = '<h1 id="cdn-maintenance-title" style="font-size:24px;margin:0 0 12px"></h1><p style="margin:0">This app is taking a short break for an update. Your work stays in this tab, and it will unlock when the update finishes.</p>';
  dialog.querySelector('h1').textContent = name + ' is updating';
  const style = document.createElement('style');
  style.textContent = 'dialog::backdrop{background:#edefebf5}';
  document.head.appendChild(style);
  document.body.appendChild(dialog);
  dialog.addEventListener('cancel', event => event.preventDefault());
  let blocked = false, firstVersion = null, lastVersion = null;
  const originalInert = new Map();
  function lockContent() {
    for (const child of document.body.children) {
      if (child === dialog || child.tagName === 'SCRIPT') continue;
      if (!originalInert.has(child)) originalInert.set(child, child.inert);
      child.inert = true;
    }
  }
  function unlockContent() {
    for (const [element, value] of originalInert) element.inert = value;
    originalInert.clear();
  }
  document.addEventListener('keydown', event => {
    if (blocked && event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  dialog.addEventListener('close', () => { if (blocked && !dialog.open) dialog.showModal(); });
  new MutationObserver(() => { if (blocked) lockContent(); }).observe(document.body, {childList:true});
  async function check() {
    try {
      const response = await fetch('/api/maintenance?app=' + encodeURIComponent(app), {cache:'no-store', signal:AbortSignal.timeout(5000)});
      if (!response.ok) throw new Error('Maintenance check unavailable');
      const state = await response.json();
      firstVersion ||= state.installed;
      if (state.blocked) {
        blocked = true;
        lockContent();
        if (!dialog.open) dialog.showModal();
      } else {
        if (blocked) { blocked = false; dialog.close(); unlockContent(); }
        if (state.installed !== firstVersion && state.installed !== lastVersion) {
          lastVersion = state.installed;
          let notice = document.getElementById('cdn-version-notice');
          if (!notice) {
            notice = document.createElement('p');
            notice.id = 'cdn-version-notice';
            notice.setAttribute('role', 'status');
            notice.style.cssText = 'position:fixed;left:16px;right:16px;bottom:16px;padding:12px 18px;margin:0;background:#fff1d7;color:#493300;border:1px solid #a07935;border-radius:12px;font:14px/1.5 system-ui;z-index:10;pointer-events:none';
            document.body.appendChild(notice);
          }
          notice.textContent = name + ' ' + state.installed + ' is ready. Save your work, then reopen the app to use it.';
        }
      }
    } catch (_) {
      // Keep a locked tab locked until the server confirms maintenance has ended.
    }
    setTimeout(check, 1500);
  }
  check();
})();
