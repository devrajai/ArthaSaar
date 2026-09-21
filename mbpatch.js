/* mbpatch.js — wire the patched functions into the router's loaders map
   (the const loaders object in app.js holds the ORIGINAL function references,
   so simply redeclaring renderAI/renderScreener is not enough). */
loaders.ai = renderAI;
loaders.screener = renderScreener;
