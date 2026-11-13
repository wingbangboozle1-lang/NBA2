/* NBA2 dashboard behaviour: filtering, sorting, and the verified-only toggle. */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  /* ---- live text filter for any table with data-filter ---- */
  ready(function () {
    document.querySelectorAll('input[data-filter]').forEach(function (input) {
      var sel = input.getAttribute('data-filter');
      var table = document.querySelector(sel);
      if (!table) return;
      var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
      function apply() {
        var q = input.value.toLowerCase().trim();
        var shown = 0;
        rows.forEach(function (tr) {
          var hit = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
          tr.style.display = hit ? '' : 'none';
          if (hit) shown++;
        });
        var out = document.querySelector('[data-count="' + sel + '"]');
        if (out) out.textContent = shown + ' of ' + rows.length + ' rows';
      }
      input.addEventListener('input', apply);
      apply();
    });

    /* ---- day / group selector ---- */
    document.querySelectorAll('select[data-group]').forEach(function (sel) {
      var group = sel.getAttribute('data-group');
      var blocks = document.querySelectorAll('[data-group-block="' + group + '"]');
      function apply() {
        var v = sel.value;
        blocks.forEach(function (b) {
          b.style.display = (v === 'all' || b.getAttribute('data-group-value') === v) ? '' : 'none';
        });
      }
      sel.addEventListener('change', apply);
      apply();
    });

    /* ---- hide-model-output toggle ---- */
    var t = document.getElementById('hideModel');
    if (t) {
      function apply() {
        document.body.classList.toggle('nomodel', t.checked);
      }
      t.addEventListener('change', apply);
      apply();
    }

    /* ---- sortable columns ---- */
    document.querySelectorAll('table[data-sort] th[data-key]').forEach(function (th) {
      th.style.cursor = 'pointer';
      th.title = 'Sort by this column';
      var table = th.closest('table');
      var key = th.getAttribute('data-key');
      var num = th.classList.contains('num');
      var dir = 1;
      th.addEventListener('click', function () {
        var tb = table.querySelector('tbody');
        var rows = Array.prototype.slice.call(tb.querySelectorAll('tr'));
        rows.sort(function (a, b) {
          var x = a.getAttribute('data-' + key), y = b.getAttribute('data-' + key);
          if (num) {
            x = x === null || x === '' ? -Infinity : parseFloat(x);
            y = y === null || y === '' ? -Infinity : parseFloat(y);
          } else {
            x = (x || '').toLowerCase(); y = (y || '').toLowerCase();
          }
          return (x < y ? -1 : x > y ? 1 : 0) * dir;
        });
        rows.forEach(function (r) { tb.appendChild(r); });
        dir = -dir;
      });
    });
  });
})();
