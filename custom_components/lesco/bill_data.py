"""Parse CCMS bill JSON: meters, history, basic charges (from bill_json / web bill shape)."""

from __future__ import annotations

import json
from typing import Any

# Order matches LESCO web bill / metersInfo rows for net-meter domestic split.
_METER_ROLES = (
    "import_offpeak",
    "import_peak",
    "export_offpeak",
    "export_peak",
)


def flatten_basic_info(bill_root: dict[str, Any]) -> dict[str, Any]:
    """Map bill.basicInfo scalars to coordinator keys (string values preserved)."""
    out: dict[str, Any] = {}
    bill = bill_root.get("bill")
    if not isinstance(bill, dict):
        return out
    bi = bill.get("basicInfo")
    if not isinstance(bi, dict):
        return out
    mapping = [
        ("ref_no", "refNo"),
        ("consumer_name", "consumerName"),
        ("bill_month", "billMonth"),
        ("net_bill", "netBill"),
        ("curr_amount_due", "currAmntDue"),
        ("tot_cur_cons", "totCurCons"),
        ("imp_peak_units", "imp_p_units"),
        ("imp_offpeak_units", "imp_op_units"),
        ("exp_peak_units", "exp_p_units"),
        ("exp_offpeak_units", "exp_op_units"),
        ("bill_due_date", "billDueDate"),
        ("meter_read_date", "meterReadDate"),
        ("consumer_contact", "consumerContactNo"),
        ("tariff_description", "tariffDescription"),
        ("cons_type", "cons_type"),
        ("net_meter_cd", "net_meter_cd"),
        ("bill_calc", "billCalc"),
    ]
    for key, src in mapping:
        v = bi.get(src)
        if v is not None:
            out[key] = str(v)
    # Alias: totCurCons is *net* billed units for net metering, not "total import".
    if "tot_cur_cons" in out:
        out["billed_net_units"] = out["tot_cur_cons"]
    return out


def parse_meters_info(bill_root: dict[str, Any]) -> dict[str, Any]:
    """Previous / present cumulative reads and billed delta per register (kWh)."""
    out: dict[str, Any] = {}
    bill = bill_root.get("bill")
    if not isinstance(bill, dict):
        return out
    meters = bill.get("metersInfo")
    if not isinstance(meters, list):
        return out
    for idx, role in enumerate(_METER_ROLES):
        if idx >= len(meters):
            break
        m = meters[idx]
        if not isinstance(m, dict):
            continue
        label = str(m.get("mtrNo", "")).strip()
        out[f"meter_{role}_label"] = label or role
        for src, suffix in (
            ("mtrKwhPrvRead", "previous_kwh"),
            ("mtrKwhPrsRead", "present_kwh"),
            ("mtrKwhConsump", "billed_kwh"),
        ):
            val = m.get(src)
            if val is None:
                continue
            try:
                out[f"meter_{role}_{suffix}"] = float(val)
            except (TypeError, ValueError):
                out[f"meter_{role}_{suffix}"] = val
    return out


def parse_billing_history(bill_root: dict[str, Any]) -> list[dict[str, str]]:
    """Up to 13 rows: month label, units (kWh net billed), payment PKR, assessment PKR."""
    bill = bill_root.get("bill")
    if not isinstance(bill, dict):
        return []
    hist = bill.get("histInfo")
    if not isinstance(hist, dict):
        return []
    rows: list[dict[str, str]] = []
    for i in range(1, 14):
        mm = hist.get(f"gbHistMM{i}")
        if mm is None or str(mm).strip() == "":
            continue
        rows.append(
            {
                "month": str(mm).strip(),
                "units": str(hist.get(f"gbHistUnits{i}", "")).strip(),
                "payment_pkr": str(hist.get(f"payment{i}", "")).strip(),
                "assessment_pkr": str(hist.get(f"gbHistAssment{i}", "")).strip(),
            }
        )
    return rows


def billing_history_json(entries: list[dict[str, str]], max_len: int = 12000) -> str:
    """Compact JSON for HA attributes (size-capped)."""
    try:
        s = json.dumps(entries, ensure_ascii=False)
    except (TypeError, ValueError):
        s = "[]"
    if len(s) > max_len:
        return s[: max_len - 20] + "…(truncated)"
    return s


def summarize_powersmart_daily(raw: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
    """Best-effort parse of dailyConsumption response; keys only if recognized."""
    out: dict[str, Any] = {}
    if raw is None:
        return out
    rows: list[Any] = []
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        for k in ("data", "dailyConsumption", "list", "result", "records"):
            v = raw.get(k)
            if isinstance(v, list):
                rows = v
                break
    if not rows:
        return out
    last = rows[-1]
    if not isinstance(last, dict):
        return out
    # Common camelCase / snake guesses from mobile APIs
    def pick(d: dict[str, Any], *names: str) -> Any:
        for n in names:
            if n in d and d[n] is not None:
                return d[n]
        return None

    def to_float(v: Any) -> float | None:
        if v is None or v == "" or v == "-":
            return None
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None

    out["daily_last_row_json"] = json.dumps(last, ensure_ascii=False)[:4000]
    out["daily_imp_peak"] = to_float(
        pick(last, "impPk", "imp_pk", "importPeak", "import_peak", "impPeak")
    )
    out["daily_imp_offpeak"] = to_float(
        pick(last, "impOp", "imp_op", "importOffPeak", "import_off_peak", "impOffPeak")
    )
    out["daily_exp_peak"] = to_float(
        pick(last, "expPk", "exp_pk", "exportPeak", "export_peak", "expPeak")
    )
    out["daily_exp_offpeak"] = to_float(
        pick(last, "expOp", "exp_op", "exportOffPeak", "export_off_peak", "expOffPeak")
    )
    day = pick(last, "date", "billDate", "day", "readDate", "meterReadDate", "label")
    if day is not None:
        out["daily_last_date"] = str(day)
    return out
