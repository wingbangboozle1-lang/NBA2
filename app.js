/* NBA2 static site enhancement.
 * The site is fully readable without JavaScript: every table is rendered into the HTML at build
 * time (see nba2/pipeline/build_site.py), so this file never fetches or computes data.
 * It does exactly one thing: when a URL carries a #FLAG-... fragment, mark that row so a reader
 * arriving from a table's flag chip can see which row they were sent to.
 */
(function () {
  "use strict";
  function revealTarget() {
    var id = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (!id) { return; }
    var el = document.getElementById(id);
    if (!el) { return; }
    el.classList.add("is-target");
    el.scrollIntoView({ block: "center" });
    setTimeout(function () { el.classList.remove("is-target"); }, 6000);
  }
  window.addEventListener("hashchange", revealTarget);
  if (document.readyState !== "loading") { revealTarget(); }
  else { document.addEventListener("DOMContentLoaded", revealTarget); }
})();
