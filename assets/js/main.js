/* NBA2 — Shared site behavior */
document.addEventListener('DOMContentLoaded', function () {
  // Highlight the current page in the nav
  const current = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-list a').forEach(function (a) {
    const href = a.getAttribute('href');
    if (href === current) a.classList.add('active');
    // also mark index active on root
    if (current === '' && href === 'index.html') a.classList.add('active');
  });
});
