// KhoaVeyon - Tùy chỉnh giao diện: áp dụng ngay khi mở trang (không nháy), lưu trên máy chủ và bản sao trong trình duyệt
const UI_KEY = 'kvUi';
const UI_DEF = {theme: 'light', accent: '#2563eb', side: 'navy', font: 100, zoom: 100, radius: 'normal', compact_nav: false, dense: false, hidden_pages: [], brand: '', tile: 'normal', anim: true};
const UI_SIDES = {navy: ['#0f1b33', '#16264a', 'Xanh đêm'], forest: ['#0f2a22', '#16382d', 'Xanh rừng'], plum: ['#2a1238', '#3a1b4d', 'Tím mận'], slate: ['#1e2430', '#2a3140', 'Xám đá'], black: ['#0b0d12', '#151922', 'Đen'], accent: ['', '', 'Theo màu chủ đạo']};
const UI_ACCENTS = ['#2563eb', '#0891b2', '#16a34a', '#ca8a04', '#ea580c', '#dc2626', '#db2777', '#7c3aed'];
let UI = Object.assign({}, UI_DEF);
try { UI = Object.assign({}, UI_DEF, JSON.parse(localStorage.getItem(UI_KEY) || '{}')); } catch (e) { /* bỏ qua */ }

function uiShade(hex, k) {   // k<0: tối hơn, k>0: nhạt hơn (trộn với trắng)
  const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255].map(v => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k));
  return '#' + c.map(v => v.toString(16).padStart(2, '0')).join('');
}
function applyUi(p) {
  p = Object.assign({}, UI_DEF, p || UI); UI = p;
  const r = document.documentElement, st = r.style;
  const dark = p.theme === 'dark' || (p.theme === 'auto' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  r.dataset.theme = dark ? 'dark' : 'light';
  st.setProperty('--primary', p.accent); st.setProperty('--primary-d', uiShade(p.accent, -0.18)); st.setProperty('--primary-l', uiShade(p.accent, 0.9));
  const sd = UI_SIDES[p.side] || UI_SIDES.navy;
  st.setProperty('--side', sd[0] || uiShade(p.accent, -0.6)); st.setProperty('--side-2', sd[1] || uiShade(p.accent, -0.45));
  st.setProperty('--radius', {sharp: '4px', normal: '14px', round: '22px'}[p.radius] || '14px');
  st.setProperty('--side-w', p.compact_nav ? '78px' : '250px');
  st.setProperty('--mtw', {small: '112px', normal: '140px', large: '190px'}[p.tile] || '140px');
  r.classList.toggle('mini', !!p.compact_nav); r.classList.toggle('dense', !!p.dense); r.classList.toggle('noanim', !p.anim);
  document.body && (document.body.style.fontSize = (14.5 * p.font / 100) + 'px');
  r.style.zoom = p.zoom === 100 ? '' : (p.zoom / 100);
  const b = document.querySelector('.brand b'); if (b) b.textContent = p.brand || 'KhoaVeyon';
  try { localStorage.setItem(UI_KEY, JSON.stringify(p)); } catch (e) { /* bỏ qua */ }
}
applyUi(UI);
document.addEventListener('DOMContentLoaded', () => applyUi(UI));
if (window.matchMedia) window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (UI.theme === 'auto') applyUi(UI); });
