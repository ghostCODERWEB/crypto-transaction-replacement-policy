"""Model per-account nonce replacements with integer percentage fee bumps and explicit rejection reasons."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    bump = integer(d["bump_percent"])
    pool = {}
    trace = []
    for tx in records(d["transactions"], "id"):
        account = identity(tx["account"])
        nonce = integer(tx["nonce"])
        fee = integer(tx["fee"])
        tip = integer(tx["tip"])
        key = (account, nonce)
        old = pool.get(key)
        accepted = True
        required_fee = required_tip = 0
        if old:
            required_fee = (old["fee"] * (100 + bump) + 99) // 100
            required_tip = (old["tip"] * (100 + bump) + 99) // 100
            accepted = (
                fee >= required_fee
                and tip >= required_tip
                and (fee > old["fee"] or tip > old["tip"])
            )
        if accepted:
            pool[key] = {
                "id": tx["id"],
                "account": account,
                "nonce": nonce,
                "fee": fee,
                "tip": tip,
            }
        trace.append(
            {
                "id": tx["id"],
                "accepted": accepted,
                "required_fee": required_fee,
                "required_tip": required_tip,
                "replaced": old["id"] if old and accepted else None,
            }
        )
    return {
        "pool": sorted(pool.values(), key=lambda t: (t["account"], t["nonce"])),
        "trace": trace,
        "accepted_count": sum(t["accepted"] for t in trace),
    }


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
