from ml.action_guard import guard_action

def test_guard_blocks_peltier_without_fan():
    a,reason=guard_action(200,peltier_allowed=True,fan_on=False,predawn=False,night=True,bus_v=12.4,spine_c=10)
    assert a==100 and reason=='fan_required'

def test_guard_blocks_shedding_outside_predawn():
    a,reason=guard_action(300,peltier_allowed=True,fan_on=True,predawn=False,night=False,bus_v=12.4,spine_c=10)
    assert a==100
