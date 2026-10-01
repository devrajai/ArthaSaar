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

function optimized6() {
  var mv = v.querySelector(".card");
  var cards2 = v.querySelectorAll(".card");
  for (var ci = 0; ci < cards2.length; ci++) {
    var sh2 = cards2[ci].querySelector(".sh2");
    if (sh2 && /Model View/i.test(sh2.textContent)) {
      mv = cards2[ci];
      break;
    }
  }
  return mv;
}

console.log("Baseline result:", !!baseline());
console.log("Optimized6 result:", !!optimized6());

function runBench(fn, name) {
  const start = Date.now();
  for(let i=0; i<100000; i++) {
    fn();
  }
  const end = Date.now();
  console.log(`${name}: ${end - start}ms`);
}

runBench(baseline, "baseline");
runBench(optimized6, "optimized6");
