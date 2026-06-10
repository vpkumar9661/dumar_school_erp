/* ==========================================================
   VVM Dharampur School ERP — main.js  FINAL
   ROOT CAUSE FIXES:
   1. Custom cursor REMOVED (was blocking all modal clicks)
   2. Global submit handler REMOVED (was disabling buttons)
   3. Modal z-index forced to 9050 (above everything)
   4. All English, no Hindi
   ========================================================== */
'use strict';

/* ── CRITICAL: Run before DOMContentLoaded ─────────────────
   Injects styles that CANNOT be overridden by cursor JS
   (cursor JS was removed from base.html but this is safety) */
(function() {
  var s = document.createElement('style');
  s.id = 'vvm-critical';
  s.textContent = [
    /* Normal OS cursor everywhere */
    '* { cursor: auto; }',
    'a, button, .btn, [role=button], select,',
    'label, .sidebar-menu li a, .topbar-icon-btn { cursor: pointer; }',
    'input, textarea, .form-control { cursor: text; }',
    '.form-select { cursor: pointer; }',

    /* Kill any cursor overlay elements */
    '#cursorGlow, #cursorDot, .cursor-glow, .cursor-dot {',
    '  display: none !important;',
    '  pointer-events: none !important;',
    '  width: 0 !important; height: 0 !important;',
    '}',

    /* Modal ABOVE everything — cursor had z-index 9998 */
    '.modal-backdrop { z-index: 9040 !important; }',
    '.modal          { z-index: 9050 !important; }',
    '.modal-dialog   { z-index: 9051 !important; }',
    '.modal-content  { z-index: 9052 !important; position: relative !important; }',

    /* All modal elements MUST be clickable */
    '.modal-body *, .modal-footer *, .modal-header * { pointer-events: auto !important; }',
    '.modal-body input, .modal-body select, .modal-body textarea,',
    '.modal-body button, .modal-footer button { cursor: pointer !important; }'
  ].join('\n');
  document.head.appendChild(s);
})();


/* ── Subtle click effect (soft glow + dots, NO circle) ─── */
(function() {
  var s = document.createElement('style');
  s.textContent = [
    '.ce-glow { position:fixed; border-radius:50%; pointer-events:none !important;',
    '  z-index:50 !important; transform:translate(-50%,-50%);',
    '  animation:ceG .35s ease-out forwards; }',
    '@keyframes ceG {',
    '  0%  { width:0;     height:0;     opacity:.5; }',
    '  60% { width:90px;  height:90px;  opacity:.18; }',
    '  100%{ width:120px; height:120px; opacity:0; } }',
    '.ce-dot { position:fixed; border-radius:50%; pointer-events:none !important;',
    '  z-index:50 !important;',
    '  animation:ceD var(--d,.38s) ease-out forwards; }',
    '@keyframes ceD {',
    '  0%  { transform:translate(-50%,-50%) translate(0,0) scale(1); opacity:.8; }',
    '  100%{ transform:translate(-50%,-50%) translate(var(--x),var(--y)) scale(0); opacity:0; } }'
  ].join('\n');
  document.head.appendChild(s);

  var COLORS = ['#00D4FF','#7C6FEF','#10E87B','#F5C842','#FF4D6D'];

  function getColor(el) {
    if (!el) return '#00D4FF';
    var p = el.closest && el.closest('.btn-success,.qa-green');
    if (p) return '#10E87B';
    p = el.closest && el.closest('.btn-danger,.btn-outline-danger');
    if (p) return '#FF4D6D';
    p = el.closest && el.closest('.btn-gold,.btn-warning');
    if (p) return '#F5C842';
    return '#00D4FF';
  }

  document.addEventListener('click', function(e) {
    var x = e.clientX, y = e.clientY, c = getColor(e.target);

    /* Glow */
    var g = document.createElement('div');
    g.className = 'ce-glow';
    g.style.cssText = 'left:' + x + 'px;top:' + y + 'px;' +
      'background:radial-gradient(circle,' + c + '35 0%,' + c + '08 60%,transparent 70%);';
    document.body.appendChild(g);
    g.addEventListener('animationend', function(){ g.remove(); }, {once:true});

    /* Dots */
    var n = e.target.closest && e.target.closest('button,a,.btn') ? 6 : 3;
    for (var i = 0; i < n; i++) {
      (function(idx){
        setTimeout(function(){
          var a = Math.random() * Math.PI * 2;
          var d = 12 + Math.random() * 28;
          var sz = 2 + Math.random() * 3;
          var dot = document.createElement('div');
          dot.className = 'ce-dot';
          dot.style.cssText = 'left:' + x + 'px;top:' + y + 'px;' +
            'width:' + sz + 'px;height:' + sz + 'px;' +
            'background:' + (idx % 3 === 0 ? '#ffffff55' : c) + ';' +
            '--x:' + (Math.cos(a)*d).toFixed(1) + 'px;' +
            '--y:' + (Math.sin(a)*d).toFixed(1) + 'px;' +
            '--d:' + (.22 + Math.random()*.16).toFixed(2) + 's;';
          document.body.appendChild(dot);
          dot.addEventListener('animationend', function(){ dot.remove(); }, {once:true});
        }, idx * 20);
      })(i);
    }
  }, { passive: true });
})();


/* ── Sidebar ──────────────────────────────────────────── */
function toggleSidebar() {
  var sb = document.getElementById('sidebar');
  var ov = document.getElementById('sidebarOverlay');
  if (!sb) return;
  var open = sb.classList.toggle('open');
  if (ov) ov.classList.toggle('show', open);
}


/* ── DOM Ready ────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {

  /* Close sidebar on overlay click */
  var ov = document.getElementById('sidebarOverlay');
  if (ov) {
    ov.addEventListener('click', function() {
      var sb = document.getElementById('sidebar');
      if (sb) sb.classList.remove('open');
      ov.classList.remove('show');
    });
  }

  /* Active sidebar link */
  var path = window.location.pathname;
  var links = document.querySelectorAll('#sidebar a[href]');
  for (var i = 0; i < links.length; i++) {
    var h = links[i].getAttribute('href');
    if (h && h !== '/' && path.indexOf(h) === 0) {
      links[i].classList.add('active');
    }
  }

  /* Auto-dismiss flash messages after 5s */
  setTimeout(function() {
    var alerts = document.querySelectorAll('.alert-dismissible');
    for (var i = 0; i < alerts.length; i++) {
      try {
        bootstrap.Alert.getOrCreateInstance(alerts[i]).close();
      } catch(e) {
        alerts[i].style.opacity = '0';
        alerts[i].style.transition = 'opacity .4s';
        setTimeout((function(el){ return function(){ el.remove(); }; })(alerts[i]), 400);
      }
    }
  }, 5000);

  /* ── ONLY delete/confirm forms get a handler ──────────
     NO global submit handler — that was disabling buttons
     and preventing form submission. Each form handles itself. */
  var confirmForms = document.querySelectorAll('form[data-confirm]');
  for (var i = 0; i < confirmForms.length; i++) {
    confirmForms[i].addEventListener('submit', function(e) {
      if (!confirm(this.getAttribute('data-confirm') || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  }

  /* Card entrance animation — skip modal children to avoid invisible modal bug */
  if (typeof IntersectionObserver !== 'undefined') {
    var allCards = document.querySelectorAll('.card,.stat-card,.aether-card,.panel-card');
    var cards = [];
    for (var ci = 0; ci < allCards.length; ci++) {
      // Do NOT animate cards inside modals
      if (!allCards[ci].closest('.modal')) {
        cards.push(allCards[ci]);
      }
    }
    var io = new IntersectionObserver(function(entries) {
      entries.forEach(function(en, i) {
        if (en.isIntersecting) {
          setTimeout(function(el){
            return function(){
              el.style.opacity = '1';
              el.style.transform = 'translateY(0)';
            };
          }(en.target), i * 40);
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.05 });

    for (var i = 0; i < cards.length; i++) {
      cards[i].style.cssText += 'opacity:0;transform:translateY(10px);' +
        'transition:opacity .25s ease,transform .25s ease;';
      io.observe(cards[i]);
    }
  }

  /* Toast container */
  if (!document.getElementById('toastWrap')) {
    var w = document.createElement('div');
    w.id = 'toastWrap';
    w.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99990;' +
      'display:flex;flex-direction:column;gap:8px;pointer-events:none;';
    document.body.appendChild(w);
  }

});


/* ── Toast notification ───────────────────────────────── */
document.head.insertAdjacentHTML('beforeend',
  '<style>' +
  '@keyframes _ti{from{transform:translateX(110%);opacity:0}to{transform:translateX(0);opacity:1}}' +
  '@keyframes _to{from{transform:translateX(0);opacity:1}to{transform:translateX(110%);opacity:0}}' +
  '</style>'
);

function showToast(msg, type, ms) {
  type = type || 'info';
  ms   = ms   || 3500;
  var map = {
    success: { bg:'rgba(16,232,123,.1)',  bd:'rgba(16,232,123,.3)',  tx:'#10E87B', ic:'fa-check-circle' },
    danger:  { bg:'rgba(255,77,109,.1)',  bd:'rgba(255,77,109,.3)',  tx:'#FF4D6D', ic:'fa-times-circle' },
    warning: { bg:'rgba(245,200,66,.1)',  bd:'rgba(245,200,66,.3)',  tx:'#F5C842', ic:'fa-exclamation-triangle' },
    info:    { bg:'rgba(0,212,255,.08)', bd:'rgba(0,212,255,.25)',  tx:'#00D4FF', ic:'fa-info-circle' }
  };
  var c = map[type] || map.info;
  var w = document.getElementById('toastWrap');
  if (!w) return;
  var t = document.createElement('div');
  t.style.cssText = 'background:' + c.bg + ';border:1px solid ' + c.bd + ';color:' + c.tx + ';' +
    'padding:11px 16px;border-radius:11px;font-size:13.5px;font-weight:600;' +
    'font-family:"Inter",sans-serif;box-shadow:0 4px 22px rgba(0,0,0,.4);' +
    'display:flex;align-items:center;gap:10px;min-width:230px;max-width:360px;' +
    'cursor:pointer;pointer-events:auto;animation:_ti .28s cubic-bezier(.34,1.56,.64,1) forwards;';
  t.innerHTML = '<i class="fas ' + c.ic + '" style="font-size:15px;flex-shrink:0;"></i>' + msg;
  w.appendChild(t);
  function rm() {
    t.style.animation = '_to .25s ease forwards';
    t.addEventListener('animationend', function(){ t.remove(); }, {once:true});
  }
  t.addEventListener('click', rm);
  setTimeout(rm, ms);
}

window.showToast = showToast;
window.formatINR = function(n) {
  return '\u20B9' + Math.round(+n).toLocaleString('en-IN');
};
