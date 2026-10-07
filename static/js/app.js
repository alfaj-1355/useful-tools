const themeBtn = document.getElementById("themeBtn");
themeBtn?.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  localStorage.setItem("alfaj-dark", document.body.classList.contains("dark") ? "1" : "0");
});
if(localStorage.getItem("alfaj-dark")==="1") document.body.classList.add("dark");

const search = document.getElementById("toolSearch");
const cards = [...document.querySelectorAll(".tool-card")];
const count = document.getElementById("count");
const empty = document.getElementById("empty");
let category = "All";

function filterTools(){
  const q=(search?.value||"").toLowerCase().trim();
  let shown=0;
  cards.forEach(c=>{
    const okCat=category==="All" || c.dataset.category===category;
    const okQ=!q || c.dataset.name.includes(q) || c.dataset.desc.includes(q);
    c.style.display=okCat&&okQ?"":"none";
    if(okCat&&okQ) shown++;
  });
  if(count) count.textContent=`${shown} tools`;
  if(empty) empty.hidden=shown!==0;
}
search?.addEventListener("input",filterTools);
document.querySelectorAll(".chip").forEach(chip=>{
  chip.addEventListener("click",()=>{
    document.querySelectorAll(".chip").forEach(x=>x.classList.remove("active"));
    chip.classList.add("active"); category=chip.dataset.category; filterTools();
  });
});
function copyResult(){
  const el=document.getElementById("resultText");
  if(el) navigator.clipboard.writeText(el.innerText).then(()=>alert("Copied to clipboard."));
}


// PWA install prompt
let deferredInstall=null;
window.addEventListener("beforeinstallprompt", e=>{e.preventDefault(); deferredInstall=e; const b=document.getElementById("installBtn"); if(b)b.hidden=false;});
document.addEventListener("click", async e=>{if(e.target.closest("#installBtn") && deferredInstall){deferredInstall.prompt(); await deferredInstall.userChoice; deferredInstall=null; e.target.closest("#installBtn").hidden=true;}});
window.addEventListener("appinstalled",()=>{const b=document.getElementById("installBtn");if(b)b.hidden=true;});
