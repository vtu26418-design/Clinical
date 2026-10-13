"""Fixed-reference descriptive PCI, independent of fitted model risk.

The JSON specification is shared with the browser. Decimal input text becomes an
exact rational before normalization, summation and half-up rounding, avoiding
binary-float ties at both category boundaries. This is not a validated score.
"""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import json
import math
from numbers import Real
from pathlib import Path
import re

FORMULA_CONFIG = json.loads((Path(__file__).resolve().parents[3] / 'configs/formulas.json').read_text(encoding='utf-8'))
PCI_SPEC = FORMULA_CONFIG['fixed_reference_pci']
METHODOLOGY = PCI_SPEC['methodology']
_DECIMAL_PATTERN = re.compile(PCI_SPEC['input_policy']['decimal_pattern'])
_COMPONENTS = PCI_SPEC['components']

if (not _COMPONENTS
        or sum(Fraction(str(part['weight'])) for part in _COMPONENTS) != 100
        or any(not math.isfinite(float(part['weight'])) or not 0 <= part['weight'] <= 100
               or not math.isfinite(float(part['ceiling'])) or part['ceiling'] <= 0 for part in _COMPONENTS)
        or len({part['key'] for part in _COMPONENTS}) != len(_COMPONENTS)
        or len({part['label'] for part in _COMPONENTS}) != len(_COMPONENTS)):
    raise ValueError('PCI requires unique components, finite positive ceilings and nonnegative weights totaling 100.')


def _decimal_value(value):
    """Return an exact finite numeric value; invalid input is disclosed upstream."""
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal, str)):
        return None
    text = str(value).strip()
    if not _DECIMAL_PATTERN.fullmatch(text):
        return None
    try:
        # Bound exact arithmetic in both runtimes before constructing a fraction.
        mantissa, *exponents = re.split('[eE]', text.lstrip('+-'))
        integer, _, fraction = mantissa.partition('.')
        digits = (integer or '0') + fraction
        exponent = int(exponents[0]) if exponents else 0
        policy = PCI_SPEC['input_policy']
        if (len(digits) > policy['max_decimal_digits']
                or abs(exponent - len(fraction)) > policy['max_absolute_decimal_scale']):
            return None
        # Browser numeric range is part of the shared scalar input contract.
        if not math.isfinite(float(text)):
            return None
        return Fraction(Decimal(text))
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None


def calculate_pci_details(row: dict) -> dict:
    """Compute the fixed reference score and disclose missing/invalid components."""
    exact_components = {}
    missing_fields = []
    for part in _COMPONENTS:
        value = _decimal_value(row.get(part['key']))
        if value is None:
            missing_fields.append(part['key'])
            value = Fraction(0)
        normalized = max(Fraction(0), min(value / Fraction(str(part['ceiling'])), Fraction(1)))
        exact_components[part['label']] = normalized * Fraction(str(part['weight']))
    total = sum(exact_components.values(), Fraction(0))
    scale = 10 ** PCI_SPEC['rounding']['digits']
    # For a nonnegative fraction, integer division rounds half upward exactly.
    cents = (2 * total.numerator * scale + total.denominator) // (2 * total.denominator)
    score = cents / scale
    category = next(part['label'] for part in PCI_SPEC['categories']
                    if score < part['upper'] or (part['upper_inclusive'] and score == part['upper']))
    return {'score': score, 'category': category,
            'components': {label: float(value) for label, value in exact_components.items()},
            'methodology': METHODOLOGY, 'missing_fields': missing_fields, 'formula_id': PCI_SPEC['id']}


def calculate_pci(row: dict):
    """Keep the v3 three-item tuple contract for callers and scripts."""
    result = calculate_pci_details(row)
    return result['score'], result['category'], result['components']
