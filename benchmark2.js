const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = `
<div id="v-gtiai">
  <div class="card">
    <div class="sh2">Other View</div>
  </div>
  <div class="card">
    <div class="sh2">Model View</div>
    <div style="padding:10px;"></div>
  </div>
</div>
`;

const dom = new JSDOM(html);
const v = dom.window.document.getElementById("v-gtiai");

function baseline() {
  var mv = v.querySelectorAll(".card")[0];
  var cards2 = Array.prototype.slice.call(v.querySelectorAll(".card"));
  for (var ci = 0; ci < cards2.length; ci++) {
    var sh2 = cards2[ci].querySelectorAll(".sh2")[0];
    if (sh2 && /Model View/i.test(sh2.textContent)) {
      mv = cards2[ci];
      break;
    }
  }
  return mv;
}

function optimized3() {
  var mv = v.querySelectorAll(".card")[0];
  var sh2s = v.querySelectorAll(".card .sh2");
  for (var i = 0; i < sh2s.length; i++) {
    if (/Model View/i.test(sh2s[i].textContent)) {
      mv = sh2s[i].parentNode;
      break;
    }
  }
  return mv;
}

function optimized4() {
  var mv = v.querySelectorAll(".card")[0];
  var sh2Elements = v.querySelectorAll(".card .sh2");
  for (var i = 0; i < sh2Elements.length; i++) {
    if (/Model View/i.test(sh2Elements[i].textContent)) {
      var p = sh2Elements[i].parentNode;
      while (p && !p.classList.contains("card")) {
        p = p.parentNode;
      }
      if (p) {
        mv = p;
        break;
      }
    }
  }
  return mv;
}

console.log("Baseline result:", !!baseline());
console.log("Optimized3 result:", !!optimized3());
console.log("Optimized4 result:", !!optimized4());

function runBench(fn, name) {
  const start = Date.now();
  for(let i=0; i<100000; i++) {
    fn();
  }
  const end = Date.now();
  console.log(`${name}: ${end - start}ms`);
}

runBench(baseline, "baseline");
runBench(optimized3, "optimized3");
runBench(optimized4, "optimized4");
