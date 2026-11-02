"""Explicit educational inventory scenarios; not measured stock or stockout probabilities."""
import math
from statistics import NormalDist
import numpy as np


def inventory_scenario(forecast, *, lead_days, on_hand, daily_std, review_days=0,
                       on_order=0, backorders=0, service_level=.95, pack_size=1, minimum_order=0):
    values = np.asarray(forecast, dtype=float)
    if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Provide nonnegative finite forecast units for one selected series.')
    for label, value in [('lead_days', lead_days), ('review_days', review_days), ('pack_size', pack_size)]:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f'{label} must be an integer.')
    if lead_days < 1 or review_days < 0 or lead_days + review_days > len(values) or pack_size < 1:
        raise ValueError('Lead/review coverage must fit the available forecast; pack size must be positive.')
    assumptions = [on_hand, on_order, backorders, daily_std, minimum_order]
    if not np.isfinite(assumptions).all() or any(value < 0 for value in assumptions):
        raise ValueError('Stock, orders, backorders, variability and minimum order must be finite and nonnegative.')
    if not np.isfinite(service_level) or not .5 <= service_level < 1:
        raise ValueError('Service level must be at least 0.5 and below 1.')
    safety = NormalDist().inv_cdf(service_level)*daily_std*math.sqrt(lead_days)
    lead_demand = float(values[:lead_days].sum())
    target = float(values[:lead_days+review_days].sum())+safety
    position = float(on_hand+on_order-backorders)
    reorder = bool(position <= lead_demand+safety)
    raw_order = max(0., target-position) if reorder else 0.
    quantity = math.ceil(max(raw_order, minimum_order)/pack_size)*pack_size if raw_order > 0 else 0
    return {'scenario_only': True, 'inventory_position': position, 'lead_time_demand': lead_demand,
            'safety_stock': float(safety), 'reorder_point': lead_demand+safety, 'target_stock': target,
            'reorder_now': reorder, 'suggested_order_units': quantity,
            'inputs': {'lead_days': lead_days, 'review_days': review_days, 'on_hand': on_hand,
                       'on_order': on_order, 'backorders': backorders, 'daily_std': daily_std,
                       'service_level': service_level, 'pack_size': pack_size, 'minimum_order': minimum_order},
            'assumptions': 'Operator-supplied what-if inputs. Safety stock = normal quantile × daily demand SD × sqrt(fixed lead time). Assumes independent daily demand and a normal approximation. Desired service level is not a measured guarantee. Sales SD may be a poor demand/error proxy. This is a reorder-point policy with a lead-plus-review target; no stockout probability is estimated.'}
