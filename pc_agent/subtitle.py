"""
Subtitle WebSocket manager for PC Agent.
OBS adds this as a Browser Source: http://localhost:8100/subtitle
"""
from fastapi import WebSocket

_connections: list[WebSocket] = []


async def connect(ws: WebSocket):
    await ws.accept()
    _connections.append(ws)


def disconnect(ws: WebSocket):
    if ws in _connections:
        _connections.remove(ws)


async def broadcast(text: str):
    dead = []
    for ws in _connections:
        try:
            await ws.send_text(text)
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect(ws)


_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: transparent;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    height: 100vh;
    padding-bottom: 40px;
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
  }
  #subtitle {
    max-width: 80%;
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    text-shadow:
      2px 2px 0 #000,
      -2px -2px 0 #000,
      2px -2px 0 #000,
      -2px 2px 0 #000,
      0 3px 8px rgba(0,0,0,0.8);
    line-height: 1.4;
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
  }
  #subtitle.show { opacity: 1; }
</style>
</head>
<body>
<div id="subtitle"></div>
<script>
  const el = document.getElementById('subtitle');
  let hideTimer = null;

  function showText(text) {
    if (hideTimer) clearTimeout(hideTimer);
    el.textContent = text;
    el.classList.add('show');
    // 字幕顯示時間：每個字 0.15s，最少 2s，最多 6s
    const duration = Math.min(Math.max(text.length * 150, 2000), 6000);
    hideTimer = setTimeout(() => {
      el.classList.remove('show');
    }, duration);
  }

  function connect() {
    const ws = new WebSocket(`ws://${location.host}/subtitle/ws`);
    ws.onmessage = e => showText(e.data);
    ws.onclose = () => setTimeout(connect, 2000);
    ws.onerror = () => ws.close();
  }
  connect();
</script>
</body>
</html>"""
