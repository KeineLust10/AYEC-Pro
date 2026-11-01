(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  if (params.get("start") !== "1") return;

  var form = document.getElementById("demo-entry-form");
  if (!form || typeof form.requestSubmit !== "function") return;

  window.setTimeout(function () {
    form.requestSubmit();
  }, 180);
})();
