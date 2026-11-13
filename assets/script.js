// NBA2 — minimal site behavior
document.addEventListener('DOMContentLoaded', function () {
  // Highlight current page in sidebar nav
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.sidebar a').forEach(function (a) {
    const href = a.getAttribute('href');
    if (href && (path === href || (path !== 'index.html' && path === href))) {
      a.classList.add('active');
    }
    if (path === 'index.html' && href === 'index.html') a.classList.add('active');
  });

  // Zebra/stripe rows already in CSS; keep tables keyboard-friendly
  document.querySelectorAll('table.data a').forEach(function (link) {
    link.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); window.open(link.href, '_blank'); }
    });
  });
});
