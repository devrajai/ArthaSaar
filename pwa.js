(function(){
"use strict";
if(!("serviceWorker" in navigator))return;
window.addEventListener("load",function(){
  navigator.serviceWorker.register("sw.js?v=2").catch(function(){});
  var link=document.createElement("link");link.rel="manifest";link.href="manifest.webmanifest?v=2";document.head.appendChild(link);
});
})();