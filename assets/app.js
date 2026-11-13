/* NBA2 — minimal, robust site interactivity (no external deps). */
(function () {
  // Active nav link based on current path.
  var path = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav a").forEach(function (a) {
    var href = a.getAttribute("href");
    if (href === path || (path === "" && href === "index.html")) {
      a.classList.add("active");
    }
  });

  // Simple text filter for tables with a [data-filter] input above them.
  document.querySelectorAll("[data-filter]").forEach(function (input) {
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      var table = input.closest("section.panel").querySelector("table");
      if (!table) return;
      table.querySelectorAll("tbody tr").forEach(function (row) {
        var text = row.textContent.toLowerCase();
        row.style.display = (q === "" || text.indexOf(q) !== -1) ? "" : "none";
      });
    });
  });
})();
