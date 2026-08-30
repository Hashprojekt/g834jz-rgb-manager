const profileId = document.body.dataset.profileId;
let state = null;
let selected = new Set();

const presets = ['#0050FF','#00FFFF','#00FF00','#FFFF00','#FF5A00','#FF0000','#AA28E6','#FFFFFF','#202020'];
const quick = document.getElementById('quickColours');
quick.innerHTML = presets.map(c => `<button class="quick-colour" data-colour="${c}" title="${c}" style="background:${c}"></button>`).join('');
quick.addEventListener('click', e => { const b=e.target.closest('[data-colour]'); if(b) setColour(b.dataset.colour); });

function hexToRgb(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return null;
  return [parseInt(m[1].slice(0,2),16),parseInt(m[1].slice(2,4),16),parseInt(m[1].slice(4,6),16)];
}
function rgbToHex(rgb){return '#'+rgb.map(v=>Math.max(0,Math.min(255,Number(v)||0)).toString(16).padStart(2,'0')).join('').toUpperCase();}
function contrast(hex){const r=hexToRgb(hex)||[0,0,0];return (r[0]*299+r[1]*587+r[2]*114)/1000>150?'#111':'#fff';}

function setColour(hex) {
  const rgb=hexToRgb(hex); if(!rgb) return;
  const normal=rgbToHex(rgb);
  document.getElementById('colourPicker').value=normal.toLowerCase();
  document.getElementById('hexInput').value=normal;
  document.getElementById('rInput').value=rgb[0];document.getElementById('gInput').value=rgb[1];document.getElementById('bInput').value=rgb[2];
}

document.getElementById('colourPicker').addEventListener('input',e=>setColour(e.target.value));
document.getElementById('hexInput').addEventListener('change',e=>{const r=hexToRgb(e.target.value);if(r)setColour(rgbToHex(r));else toast('Nieprawidłowy HEX.',true);});
for(const id of ['rInput','gInput','bInput']) document.getElementById(id).addEventListener('change',()=>setColour(rgbToHex([
  document.getElementById('rInput').value,document.getElementById('gInput').value,document.getElementById('bInput').value])));

function updateSelection() {
  document.getElementById('selectionCount').textContent=selected.size;
  document.getElementById('selectionNames').textContent=selected.size?[...selected].join(', '):'Kliknij klawisze poniżej';
  document.querySelectorAll('.key[data-key]').forEach(k=>k.classList.toggle('selected',selected.has(k.dataset.key)));
}

function selectOnly(ids) {
  selected.clear();
  for(const id of ids){if(state?.keys[id]?.editable)selected.add(id);}
  updateSelection();
}

function buildKeyboardRows(root, rows) {
  root.innerHTML='';
  for(const row of rows){
    const rowEl=document.createElement('div');rowEl.className='keyboard-row';
    for(const item of row){
      if(item.gap){const gap=document.createElement('div');gap.className='key-gap';gap.style.setProperty('--u',item.gap);rowEl.appendChild(gap);continue;}
      const info=state.keys[item.id]||{mapped:false,editable:false,dynamic:false,hex:null};
      const key=document.createElement('button');key.className='key';key.dataset.key=item.id;key.style.setProperty('--u',item.w||1);
      if(item.id==='SPACE') key.classList.add('space-key');
      if(item.id.startsWith('NUM')) key.classList.add('numpad-key');
      if(/^F\d+$/.test(item.id)) key.classList.add('function-key');
      key.innerHTML=`<span>${escapeHtml(item.label)}</span>`;
      if(info.dynamic){key.classList.add('dynamic');key.disabled=true;key.title='Sterowany dynamicznie';}
      else if(!info.mapped){key.classList.add('unknown');key.disabled=true;key.title='Brak bezpiecznego mapowania RGB';}
      else {key.style.background=info.hex;key.style.color=contrast(info.hex);key.title=`${item.label} · ${info.hex}`;key.addEventListener('click',()=>{
        if(selected.has(item.id)) selected.delete(item.id); else selected.add(item.id);
        if(selected.size===1) setColour(info.hex); updateSelection();
      });}
      rowEl.appendChild(key);
    }
    root.appendChild(rowEl);
  }
}

function renderKeyboard() {
  const functionRoot=document.getElementById('functionKeyboard');
  const mainRoot=document.getElementById('keyboard');
  buildKeyboardRows(functionRoot,state.layout.slice(0,2));
  buildKeyboardRows(mainRoot,state.layout.slice(2));
  updateSelection();
}

function renderPalette(){
  const root=document.getElementById('palette');document.getElementById('paletteCount').textContent=`${state.palette.length} kolorów`;
  root.innerHTML=state.palette.map((p,i)=>`<button class="palette-swatch" data-index="${i}" title="${p.hex}" style="background:${p.hex}"><span>${p.count}</span></button>`).join('');
  root.onclick=e=>{
    const sw=e.target.closest('[data-index]');if(!sw)return;const p=state.palette[Number(sw.dataset.index)];
    const ids=Object.entries(state.keys).filter(([,v])=>v.editable&&v.hex===p.hex).map(([k])=>k);selectOnly(ids);setColour(p.hex);
    root.querySelectorAll('.palette-swatch').forEach(x=>x.classList.toggle('selected',x===sw));
  };
}

async function loadState(){
  state=await api(`/api/profiles/${profileId}/keyboard`);renderKeyboard();renderPalette();
  document.getElementById('undoBtn').disabled=!state.can_undo;document.getElementById('redoBtn').disabled=!state.can_redo;
}

document.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>selectOnly(state.groups[b.dataset.group]||[])));
document.getElementById('allMappedBtn').addEventListener('click',()=>selectOnly(Object.entries(state.keys).filter(([,v])=>v.editable).map(([k])=>k)));
document.getElementById('clearSelectionBtn').addEventListener('click',()=>{selected.clear();updateSelection();});

document.getElementById('applyBtn').addEventListener('click',async()=>{
  if(!selected.size){toast('Najpierw zaznacz klawisze.',true);return;}
  const rgb=hexToRgb(document.getElementById('hexInput').value);if(!rgb){toast('Nieprawidłowy kolor.',true);return;}
  try{const data=await api(`/api/profiles/${profileId}/keys`,{method:'POST',body:JSON.stringify({keys:[...selected],rgb})});
    selected.clear();await loadState();toast(data.changed.length?`Zmieniono: ${data.changed.join(', ')}`:'Kolor już był ustawiony.');}
  catch(e){toast(e.message,true);}
});

async function history(direction){try{await api(`/api/profiles/${profileId}/${direction}`,{method:'POST'});selected.clear();await loadState();toast(direction==='undo'?'Cofnięto zmianę.':'Ponowiono zmianę.');}catch(e){toast(e.message,true);}}
document.getElementById('undoBtn').addEventListener('click',()=>history('undo'));
document.getElementById('redoBtn').addEventListener('click',()=>history('redo'));

loadState().catch(e=>toast(e.message,true));
