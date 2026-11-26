from ml.runtime_monitor import check_row

def test_detects_peltier_without_fan():
    faults = check_row({'peltier':1,'fan':0,'air_temp_c':20,'rh_pct':80,'dew_point_c':18,'spine_temp_c':10,'bus_v':12.4,'wh_total':1})
    codes = {f['code'] for f in faults}
    assert 'SAFETY_PELTIER_NO_FAN' in codes

def test_detects_range_and_nonmonotonic():
    prev = {'timestamp_ms':100,'flow_l_total':2.0}
    row = {'timestamp_ms':90,'flow_l_total':1.0,'air_temp_c':200,'rh_pct':50,'dew_point_c':10,'spine_temp_c':10,'bus_v':12,'wh_total':1}
    codes = {f['code'] for f in check_row(row, prev)}
    assert 'RANGE_AIR_TEMP_C' in codes
    assert 'FLOW_NON_MONOTONIC' in codes
    assert 'TIME_NON_MONOTONIC' in codes
