import json, threading, time, urllib.request
from software.cloud.api import Handler
from http.server import HTTPServer

def test_decide_endpoint():
    srv = HTTPServer(('127.0.0.1',0), Handler)
    t = threading.Thread(target=srv.handle_request)
    t.start()
    port = srv.server_port
    payload = json.dumps({"air_temp_c":14,"rh_pct":92,"dew_point_c":13,"spine_temp_c":12,"soil_a_pct":60,"soil_b_pct":60,"hour":5.5}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{port}/api/decide', data=payload, headers={'Content-Type':'application/json'})
    resp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
    t.join(timeout=2); srv.server_close()
    assert 'selected' in resp and 'why' in resp
