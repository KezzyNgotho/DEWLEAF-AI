"""Structured events and simple metrics for DewLeaf."""
from __future__ import annotations
import json, time
from collections import Counter
from pathlib import Path

EVENTS = Path('logs/events.jsonl')
METRICS = Counter()
START = time.time()

def emit(event_type: str, payload: dict):
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    rec={'ts':time.time(),'type':event_type, **payload}
    with EVENTS.open('a',encoding='utf-8') as f: f.write(json.dumps(rec)+'\n')
    METRICS[event_type]+=1

def snapshot():
    return {'uptime_s':time.time()-START,'counters':dict(METRICS)}
