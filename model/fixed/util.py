"""integer arithmetic primitives shared by every fixed point block,
round half up means add 1 << (shift-1) then arithmetic shift right,
every narrowing step saturates and can report into a sticky flags dict,
int64 carries everything, widest product is s19 * s18 = 37 bits
"""

import numpy as np


def rhu(x, shift):
    """round half up then arithmetic shift right, shift 0 is a no op,
    rounds toward +inf for negatives, rhu(-3, 1) = -1"""
    x = np.asarray(x, dtype=np.int64)
    if shift == 0:
        return x.copy()
    return (x + (np.int64(1) << np.int64(shift - 1))) >> np.int64(shift)


def sat_signed(x, bits, flags=None, stage=None):
    """saturate to a signed range, sets flags[stage] sticky true on clip"""
    x = np.asarray(x, dtype=np.int64)
    lo = -(np.int64(1) << np.int64(bits - 1))
    hi = (np.int64(1) << np.int64(bits - 1)) - 1
    clipped = np.clip(x, lo, hi)
    if flags is not None and stage is not None:
        flags[stage] = bool(flags.get(stage, False) or np.any(x != clipped))
    return clipped


def sat_unsigned(x, bits, flags=None, stage=None):
    x = np.asarray(x, dtype=np.int64)
    hi = (np.int64(1) << np.int64(bits)) - 1
    clipped = np.clip(x, 0, hi)
    if flags is not None and stage is not None:
        flags[stage] = bool(flags.get(stage, False) or np.any(x != clipped))
    return clipped


def rdiv(num, den):
    """round half up integer division for num >= 0 and den > 0, equals
    rhu by log2(den) when den is a power of two"""
    return (int(num) + int(den) // 2) // int(den)
