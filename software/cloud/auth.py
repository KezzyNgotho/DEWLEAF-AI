import os, hmac
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[2] / 'logs' / 'audit.jsonl'

def check_auth(headers) -> bool:
    token = os.environ.get('DEWLEAF_API_TOKEN','')
    if not token: return True  # local dev default; set token in prod
    got = headers.get('Authorization','')
    return hmac.compare_digest(got, f'Bearer {token}')

def audit(event: str, detail: dict):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    import json, datetime
    rec={'ts':datetime.datetime.utcnow().isoformat()+'Z','event':event,'detail':detail}
    with AUDIT.open('a',encoding='utf-8') as f: f.write(json.dumps(rec)+'\n')
