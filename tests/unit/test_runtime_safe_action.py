from ml.runtime_monitor import check_row, recommended_safe_action

def test_recommends_safe_action_on_critical_fault():
    faults=check_row({'peltier':1,'fan':0,'air_temp_c':20,'rh_pct':80,'dew_point_c':18,'spine_temp_c':10,'bus_v':12.4,'wh_total':1})
    safe=recommended_safe_action(faults)
    assert safe['action_id']==100
