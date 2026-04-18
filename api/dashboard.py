from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kunomi Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0d14; color: #e0e0f0; font-family: 'Segoe UI', sans-serif; padding: 24px; }
  h1 { font-size: 1.4rem; color: #a78bfa; margin-bottom: 12px; letter-spacing: 2px; }
  .key-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
  .key-bar input { margin: 0; width: 260px; font-family: monospace; }
  .key-bar span { font-size: 0.8rem; color: #7c7ca0; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; max-width: 900px; }
  .card { background: #16161f; border: 1px solid #2a2a3a; border-radius: 10px; padding: 16px; }
  .card h2 { font-size: 0.85rem; color: #7c7ca0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
  input, textarea, select { width: 100%; background: #0d0d14; border: 1px solid #2a2a3a; color: #e0e0f0;
    padding: 8px 10px; border-radius: 6px; font-size: 0.9rem; margin-bottom: 8px; outline: none; }
  input:focus, textarea:focus { border-color: #a78bfa; }
  button { background: #a78bfa; color: #0d0d14; border: none; padding: 8px 16px; border-radius: 6px;
    font-weight: 700; cursor: pointer; font-size: 0.85rem; transition: background 0.2s; }
  button:hover { background: #c4b5fd; }
  button:disabled { background: #3a3a50; color: #6060a0; cursor: not-allowed; }
  .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .event-btn { background: #1e1e2e; border: 1px solid #2a2a3a; color: #a78bfa; padding: 7px 14px;
    border-radius: 6px; cursor: pointer; font-size: 0.85rem; transition: all 0.15s; }
  .event-btn:hover { background: #a78bfa; color: #0d0d14; }
  .log { background: #0a0a10; border: 1px solid #1a1a2a; border-radius: 6px; padding: 10px;
    font-family: monospace; font-size: 0.8rem; height: 200px; overflow-y: auto; margin-top: 8px; }
  .log .ok { color: #86efac; }
  .log .err { color: #f87171; }
  .log .info { color: #7dd3fc; }
  .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
  .status-ok { background: #86efac; }
  .status-err { background: #f87171; }
  .status-row { display: flex; align-items: center; font-size: 0.85rem; margin-bottom: 6px; }
  #response-box { background: #0a0a10; border: 1px solid #1a1a2a; border-radius: 6px; padding: 10px;
    font-size: 0.9rem; min-height: 48px; color: #c4b5fd; margin-top: 8px; white-space: pre-wrap; }
  .full-width { grid-column: 1 / -1; }
</style>
</head>
<body>
<h1>⬡ KUNOMI DASHBOARD</h1>
<div class="key-bar">
  <input id="api-key" type="password" placeholder="API Key（留空則不帶）" oninput="saveKey()">
  <span id="key-hint"></span>
</div>
<div class="grid">

  <!-- 狀態 -->
  <div class="card">
    <h2>系統狀態</h2>
    <div class="status-row"><span class="status-dot" id="mac-dot"></span><span id="mac-status">Mac API — 檢查中…</span></div>
    <div class="status-row"><span class="status-dot" id="pc-dot"></span><span id="pc-status">PC Agent — 檢查中…</span></div>
    <button onclick="checkHealth()" style="margin-top:8px">重新整理</button>
  </div>

  <!-- 聊天測試 -->
  <div class="card">
    <h2>聊天室訊息</h2>
    <input id="chat-user" placeholder="使用者名稱" value="觀眾">
    <input id="chat-msg" placeholder="訊息內容" onkeydown="if(event.key==='Enter')sendChat()">
    <button onclick="sendChat()">送出</button>
    <div id="response-box">（回應會顯示在這裡）</div>
  </div>

  <!-- 事件觸發 -->
  <div class="card">
    <h2>觸發事件</h2>
    <div class="btn-row">
      <button class="event-btn" onclick="triggerEvent('death')">死亡</button>
      <button class="event-btn" onclick="triggerEvent('win')">勝利</button>
      <button class="event-btn" onclick="triggerEvent('idle',{seconds:30})">冷場</button>
      <button class="event-btn" onclick="triggerEvent('screenshot')">截圖</button>
    </div>
    <div id="event-response-box" style="background:#0a0a10;border:1px solid #1a1a2a;border-radius:6px;padding:10px;font-size:0.9rem;min-height:48px;color:#c4b5fd;margin-top:8px;white-space:pre-wrap;">（事件回應）</div>
  </div>

  <!-- 音效 -->
  <div class="card">
    <h2>音效板</h2>
    <div class="btn-row">
      <button class="event-btn" onclick="playSound('death')">death</button>
      <button class="event-btn" onclick="playSound('win')">win</button>
      <button class="event-btn" onclick="playSound('fail')">fail</button>
    </div>
  </div>

  <!-- Log -->
  <div class="card full-width">
    <h2>操作紀錄</h2>
    <div class="log" id="log"></div>
  </div>

</div>

<script>
const API = '';  // same origin

function getKey() { return localStorage.getItem('kunomi_api_key') || ''; }
function saveKey() {
  const k = document.getElementById('api-key').value;
  localStorage.setItem('kunomi_api_key', k);
  document.getElementById('key-hint').textContent = k ? 'saved' : 'no key';
}
function apiHeaders(extra={}) {
  const k = getKey();
  return k ? {'Content-Type':'application/json','X-API-Key':k,...extra}
           : {'Content-Type':'application/json',...extra};
}

function log(msg, cls='info') {
  const el = document.getElementById('log');
  const ts = new Date().toLocaleTimeString('zh-TW');
  el.innerHTML += `<div class="${cls}">[${ts}] ${msg}</div>`;
  el.scrollTop = el.scrollHeight;
}

async function checkHealth() {
  try {
    const r = await fetch(API + '/health');
    const d = await r.json();
    document.getElementById('mac-dot').className = 'status-dot status-ok';
    document.getElementById('mac-status').textContent = `Mac API — OK (${d.character})`;
    log('Mac API health OK', 'ok');
  } catch(e) {
    document.getElementById('mac-dot').className = 'status-dot status-err';
    document.getElementById('mac-status').textContent = 'Mac API — 無法連線';
    log('Mac API health FAILED', 'err');
  }
  // PC Agent health is checked server-side; just show a note
  document.getElementById('pc-dot').className = 'status-dot status-ok';
  document.getElementById('pc-status').textContent = 'PC Agent — 見 logs/pc_agent.log';
}

async function sendChat() {
  const msg = document.getElementById('chat-msg').value.trim();
  const user = document.getElementById('chat-user').value.trim() || '觀眾';
  if (!msg) return;
  log(`送出聊天：[${user}] ${msg}`);
  document.getElementById('response-box').textContent = '…';
  try {
    const r = await fetch(API + '/chat', {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify({message: msg, username: user})
    });
    const d = await r.json();
    document.getElementById('response-box').textContent = d.response ?? JSON.stringify(d);
    log('回應：' + (d.response ?? '').slice(0, 60), 'ok');
  } catch(e) {
    document.getElementById('response-box').textContent = '錯誤：' + e;
    log('sendChat 錯誤：' + e, 'err');
  }
  document.getElementById('chat-msg').value = '';
}

async function triggerEvent(type, context={}) {
  log(`觸發事件：${type}`);
  document.getElementById('event-response-box').textContent = '…';
  try {
    const r = await fetch(API + '/event', {
      method: 'POST',
      headers: apiHeaders(),
      body: JSON.stringify({event_type: type, context})
    });
    const d = await r.json();
    document.getElementById('event-response-box').textContent = d.response ?? JSON.stringify(d);
    log(`事件 [${type}] 回應：` + (d.response ?? '').slice(0, 60), 'ok');
  } catch(e) {
    document.getElementById('event-response-box').textContent = '錯誤：' + e;
    log('triggerEvent 錯誤：' + e, 'err');
  }
}

async function playSound(name) {
  log(`音效：${name}`);
  try {
    await fetch(API + '/soundboard/' + name, {method: 'POST', headers: apiHeaders()});
    log(`音效 [${name}] 已觸發`, 'ok');
  } catch(e) {
    log('playSound 錯誤：' + e, 'err');
  }
}

// restore saved key
const _savedKey = getKey();
if (_savedKey) {
  document.getElementById('api-key').value = _savedKey;
  document.getElementById('key-hint').textContent = 'saved';
}

checkHealth();
setInterval(checkHealth, 30000);
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    return HTMLResponse(content=_HTML)
