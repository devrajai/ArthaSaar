/* mbpatch.js — wire the patched functions into the router's loaders map
   (the const loaders object in oldapp.js holds the ORIGINAL function
   references, so redeclaring renderAI/renderScreener is not enough),
   then re-render the current section so direct links get the new view. */
loaders.ai = renderAI;
loaders.screener = renderScreener;
(function () {
  var cur = (location.hash || "#home").replace("#/", "#").split("/")[0] || "home";
  if (cur !== "home" && cur !== "lock" && loaders[cur]) {
    loaded.delete(cur);
    showView(cur);
  }
})();
