/* JinX X4G panel add-on: marks the protected inbound with the panel's own lock icon. */
(function () {
  'use strict';
  var NAME = '\uD835\uDDDD\uD835\uDDF6\uD835\uDDFB\uD835\uDDEB X4G';
  var P = 'M832 464h-68V240c0-70.7-57.3-128-128-128H388c-70.7 0-128 57.3-128 128v224h-68c-17.7 0-32 14.3-32 32v384c0 17.7 14.3 32 32 32h640c17.7 0 32-14.3 32-32V496c0-17.7-14.3-32-32-32zM332 240c0-30.9 25.1-56 56-56h248c30.9 0 56 25.1 56 56v224H332V240zm460 600H232V536h560v304zM484 701v53c0 4.4 3.6 8 8 8h40c4.4 0 8-3.6 8-8v-53a48.01 48.01 0 1 0-56 0z';
  var TIP = { fa: 'محافظت‌شده توسط سیستم', en: 'Protected by the system', ru: 'Защищено системой', zh: '系统保护', tr: 'Sistem tarafından korunuyor' };
  function lang() { var m = document.cookie.match(/(?:^|;\s*)lang=([a-z]{2})/i); return m ? m[1].toLowerCase() : 'fa'; }
  function icon() {
    var i = document.createElement('i');
    i.className = 'anticon jx-lock';
    i.setAttribute('aria-label', 'icon: lock');
    i.title = TIP[lang()] || TIP.en;
    i.style.cssText = 'margin-inline-start:6px;color:#008771;vertical-align:-0.125em;font-size:14px';
    i.innerHTML = '<svg viewBox="64 64 896 896" width="1em" height="1em" fill="currentColor" aria-hidden="true"><path d="' + P + '"></path></svg>';
    return i;
  }
  function mark(root) {
    try {
      var cells = (root || document).querySelectorAll('td, .ant-table-cell, .ant-tag, span');
      for (var k = 0; k < cells.length; k++) {
        var el = cells[k];
        if (el.getAttribute('data-jx') || el.querySelector('[data-jx]') || el.closest('[data-jx]')) continue;
        var t = (el.textContent || '').trim();
        if (t !== NAME) continue;
        var inner = false;
        for (var c = 0; c < el.children.length; c++) { if ((el.children[c].textContent || '').trim() === NAME) { inner = true; break; } }
        if (inner) continue;
        el.setAttribute('data-jx', '1'); el.appendChild(icon());
      }
    } catch (e) { /* never break the panel */ }
  }
  var pend = false;
  function soon() { if (pend) return; pend = true; setTimeout(function () { pend = false; mark(); }, 250); }
  function start() {
    mark();
    try { new MutationObserver(soon).observe(document.body, { childList: true, subtree: true }); } catch (e) {}
    try { if (window.fetch) fetch('/__jx_seen', { credentials: 'omit', cache: 'no-store' }).catch(function () {}); } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
