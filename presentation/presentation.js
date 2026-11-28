'use strict';
const $ = id => document.getElementById(id);
let slides = [], current = 0, elapsed = 0, running = false, startedAt = 0;
const format = seconds => `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
function renderTimer() {
  const seconds = Math.floor(elapsed + (running ? (performance.now() - startedAt) / 1000 : 0));
  $('timer').textContent = `${format(seconds)} / 5:00`;
  $('timer').classList.toggle('overtime', seconds > 300);
}
function toggleTimer() {
  if (running) elapsed += (performance.now() - startedAt) / 1000;
  else startedAt = performance.now();
  running = !running;
  $('start').textContent = running ? 'Pause timer' : 'Start timer';
  $('start').setAttribute('aria-label', running ? 'Pause rehearsal timer' : 'Start rehearsal timer');
  renderTimer();
}
function resetTimer() { elapsed = 0; running = false; $('start').textContent = 'Start timer'; $('start').setAttribute('aria-label','Start rehearsal timer'); renderTimer(); }
function setNotes(open) { $('notes-panel').hidden = !open; $('notes-toggle').setAttribute('aria-expanded', String(open)); }
function go(index) {
  if (!slides.length) return;
  current = Math.max(0, Math.min(slides.length - 1, index));
  const item = slides[current];
  $('slide').src = item.image;
  $('slide').alt = `Slide ${current + 1}: ${item.text}`;
  $('counter').textContent = `${current + 1} / ${slides.length}`;
  $('previous').disabled = current === 0;
  $('next').disabled = current === slides.length - 1;
  $('notes-title').textContent = item.title;
  $('notes').textContent = item.notes;
  const from = slides.slice(0,current).reduce((sum, s) => sum + s.duration,0);
  $('slide-target').textContent = `Target: ${format(item.duration)} · Talk ${format(from)}–${format(from + item.duration)}`;
  history.replaceState(null, '', `#/${current + 1}`);
  document.title = `Lex Aperta · ${current + 1}/${slides.length} · ${item.title}`;
}
function fromHash() { const found = location.hash.match(/^#\/(\d+)$/); go(found ? Number(found[1]) - 1 : 0); }
async function fullscreen() {
  try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
  catch { $('fullscreen').textContent = 'Use browser full screen'; }
}
$('previous').addEventListener('click', () => go(current - 1));
$('next').addEventListener('click', () => go(current + 1));
$('start').addEventListener('click', toggleTimer);
$('reset').addEventListener('click', resetTimer);
$('notes-toggle').addEventListener('click', () => setNotes($('notes-panel').hidden));
$('notes-close').addEventListener('click', () => { setNotes(false); $('notes-toggle').focus(); });
$('fullscreen').addEventListener('click', fullscreen);
window.addEventListener('hashchange', fromHash);
window.addEventListener('keydown', event => {
  if (event.ctrlKey || event.metaKey || event.altKey || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
  if ((event.key === ' ' || event.key === 'Enter') && /BUTTON|A|SUMMARY/.test(event.target.tagName)) return;
  const action = {ArrowRight:()=>go(current+1),PageDown:()=>go(current+1),' ':()=>go(current+1),ArrowLeft:()=>go(current-1),PageUp:()=>go(current-1),Home:()=>go(0),End:()=>go(slides.length-1),n:()=>setNotes($('notes-panel').hidden),f:fullscreen,t:toggleTimer,r:resetTimer,Escape:()=>setNotes(false)}[event.key];
  if (action) { event.preventDefault(); action(); }
});
let touchX = null;
$('stage').addEventListener('touchstart', event => { touchX = event.changedTouches[0].clientX; }, {passive:true});
$('stage').addEventListener('touchend', event => { if (touchX === null) return; const delta = event.changedTouches[0].clientX - touchX; if (Math.abs(delta) > 60) go(current + (delta < 0 ? 1 : -1)); touchX = null; }, {passive:true});
fetch('deck.json').then(response => { if (!response.ok) throw new Error('Deck unavailable'); return response.json(); }).then(data => {
  slides = data;
  slides.forEach(item => { const image = new Image(); image.src = item.image; });
  fromHash();
}).catch(() => { $('slide').hidden=true; $('error').hidden=false; $('error').textContent='The slides could not load. Please reload, or download the PowerPoint below.'; });
setInterval(renderTimer, 250);
