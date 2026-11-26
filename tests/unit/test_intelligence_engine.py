from ml.intelligence_engine import Context, decide, estimate_reward, physics_features, SAFETY, ACTIONS

def test_frost_guard_blocks_peltier():
    c = Context(air_c=10,rh_pct=95,dew_point_c=9.5,spine_c=1.0,soil_a_pct=60,soil_b_pct=60,hour=2)
    d = decide(c)
    assert d['selected']['action_id'] not in (200,201,310) or d['selected']['pred_wh'] == 0

def test_predawn_prefers_shedding():
    c = Context(air_c=14,rh_pct=92,dew_point_c=13.0,spine_c=12.0,soil_a_pct=60,soil_b_pct=60,hour=5.5,cloud_pct=20,wind_kmh=2)
    d = decide(c)
    assert d['features']['predawn'] is True
    assert d['selected']['action_id'] in (300,301,302,310)

def test_decision_trace_has_why_and_confidence():
    c = Context(air_c=16,rh_pct=85,dew_point_c=14,spine_c=13,soil_a_pct=55,soil_b_pct=55,hour=10)
    d = decide(c)
    assert 'why' in d and len(d['why']) >= 3
    assert 'selected' in d and 'top3' in d
    assert 'confidence' in d and d['confidence']['label'] in ('low','medium','high')
    assert 'safe_fallback' in d and d['safe_fallback']['action_id'] == 100
    assert 'model_source' in d

def test_low_bus_voltage_blocks_peltier_reward_path():
    c = Context(air_c=12,rh_pct=95,dew_point_c=11.5,spine_c=10,soil_a_pct=60,soil_b_pct=60,hour=2,bus_v=10.8)
    f = physics_features(c)
    nuc = next(a for a in ACTIONS if a['id']==200)
    r = estimate_reward(c,nuc,f)
    assert r['pred_wh'] == 0
