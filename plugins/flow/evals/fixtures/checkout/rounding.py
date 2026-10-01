"""Disposable evaluation fixture: truncation deliberately violates checkout rounding."""

from decimal import Decimal


def minor_units(amount):
    """Convert a decimal currency string to minor units (currently truncates)."""
    return int(Decimal(amount) * 100)
