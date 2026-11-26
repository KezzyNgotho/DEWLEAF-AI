#!/usr/bin/env python3
"""Simple DewLeaf dashboard for replay/API inspection."""
from __future__ import annotations
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[2]
REPLAY = ROOT / 'ml/artifacts/hil_replay.json'
TELEM = ROOT / 'logs/cloud_telemetry.csv'

HTML = """<!doctype html><html><head><meta charset=utf-8><title>DewLeaf Dashboard</title>
<style>body{font-family:system-ui;margin:24px;background:#0b1020;color:#e8eefc} .card{background:#151c2f;padding:16px;border-radius:12px;margin-bottom:16px} table{width:100%;border-collapse:collapse} td,th{padding:6px;border-bottom:1px solid #2a3557;font-size:13px;text-align:left} .ok{color:#7CFC98}.warn{color:#ffd166}.crit{color:#ff6b6b} code{background:#0b1020;padding:2px 4px;border-radius:4px}</style></head>
<body><h1>DewLeaf Software Twin Dashboard</h1>
<div class=card><h3>Replay Summary</h3><div id=sum>loading...</div></div>
<div class=card><h3>Recent Events</h3><table id=tbl><thead><tr><th>time</th><th>night</th><th>action</th><th>conf</th><th>faults</th><th>why</th></tr></thead><tbody></tbody></table></div>
<script>
async function load(){const r=await fetch('/api/replay'); const d=await r.json();
document.getElementById('sum').innerHTML=`rows <code>${d.rows}</code> faults <code>${d.fault_count}</code>`;
const tb=document.querySelector('#tbl tbody'); tb.innerHTML='';
(d.events||[]).slice(-50).reverse().forEach(e=>{const cls=e.faults.some(f=>f.severity==='critical')?'crit':e.faults.length?'warn':'ok';
tb.insertAdjacentHTML('beforeend',`<tr class=${cls}><td>${(e.iso_time||'').slice(11,19)}</td><td>${e.night_id||''}</td><td>${e.decision?.action||''}</td><td>${e.confidence?.label||''}</td><td>${e.faults.length}</td><td>${(e.why||[]).slice(-1)[0]||''}</td></tr>`);});}
load(); setInterval(load,5000);
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ct='application/json'):
        b=body if isinstance(body,(bytes,bytearray)) else body.encode()
        self.send_response(code); self.send_header('Content-Type',ct); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path)
        if p.path=='/': return self._send(200, HTML, 'text/html; charset=utf-8')
        if p.path=='/api/replay':
            if REPLAY.exists(): return self._send(200, REPLAY.read_bytes(), 'application/json')
            return self._send(200, json.dumps({'rows':0,'fault_count':0,'events':[]}))
        if p.path=='/health': return self._send(200, json.dumps({'ok':True}))
        return self._send(404, json.dumps({'error':'not found'}))

if __name__=='__main__':
    port=int(os.environ.get('PORT','8090'))
    print(f'DewLeaf dashboard http://0.0.0.0:{port}')
    HTTPServer(('0.0.0.0',port),H).serve_forever()
