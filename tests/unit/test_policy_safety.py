from pathlib import Path

def test_firmware_has_safety_interlocks():
    s = Path('firmware/dewleaf_firmware/src/main.cpp').read_text()
    assert 'FROST_GUARD_C' in s
    assert 'never run peltier without fan' in s.lower() or 'act.fan = true' in s
    assert 'esp_task_wdt_' in s
    assert 'PIN_SOIL_A' in Path('firmware/dewleaf_firmware/src/config.h').read_text()
