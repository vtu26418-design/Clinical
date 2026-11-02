import pytest
from src.inventory import inventory_scenario


def test_known_inventory_position_and_pack_rounding():
    result = inventory_scenario([10, 20, 30, 40, 50, 60, 70], lead_days=2, review_days=1,
                                on_hand=10, on_order=0, backorders=5, daily_std=0, pack_size=6)
    assert result['inventory_position'] == 5
    assert result['lead_time_demand'] == 30
    assert result['target_stock'] == 60
    assert result['suggested_order_units'] == 60
    assert result['reorder_now'] is True
    assert result['scenario_only'] is True


def test_no_order_above_reorder_point():
    result = inventory_scenario([10]*7, lead_days=2, on_hand=100, daily_std=0)
    assert result['suggested_order_units'] == 0


def test_safety_stock_uses_stated_service_level():
    result = inventory_scenario([10]*7, lead_days=4, on_hand=0, daily_std=2, service_level=.95)
    assert result['safety_stock'] == pytest.approx(6.5794145078)


@pytest.mark.parametrize('kwargs', [{'lead_days': 8}, {'lead_days': 2, 'review_days': 6},
    {'on_hand': -1}, {'service_level': 1}, {'pack_size': 0}, {'daily_std': float('nan')}, {'lead_days': 1.5}])
def test_invalid_scenarios_fail_instead_of_fabricating_inputs(kwargs):
    inputs = dict(lead_days=2, on_hand=0, daily_std=0)
    inputs.update(kwargs)
    with pytest.raises(ValueError):
        inventory_scenario([10]*7, **inputs)
