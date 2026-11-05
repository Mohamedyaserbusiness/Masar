"""Unit tests: Egyptian identity rules, synthetic data quality, auth primitives, suitability, forecasting honesty, fraud."""
from datetime import date

import numpy as np
import pytest

from masar import egypt as E, recommend as R, security as S
from masar.datagen import generate
from masar.pipeline import dq_checks


# ---------- Egyptian identity ----------
def test_national_id_roundtrip():
    nid = E.make_national_id(date(1995, 1, 12), "01", male=False, serial=50)
    assert len(nid) == 14 and E.validate_national_id(nid)[0]
    assert E.nid_birth_gender(nid) == (date(1995, 1, 12), "F")
    assert E.nid_birth_gender(E.make_national_id(date(2003, 7, 1), "21", True, 7))[1] == "M"


@pytest.mark.parametrize("bad", ["123", "19501120100503", "29513320100503", "29501129900503", "2950112010050x"])
def test_national_id_rejects_bad(bad):
    assert not E.validate_national_id(bad)[0]


def test_iban_mod97():
    iban = E.make_iban(101, 1234567)
    assert iban.startswith("EG") and len(iban) == 29 and E.validate_iban(iban)
    assert not E.validate_iban(iban[:-1] + str((int(iban[-1]) + 1) % 10))


@pytest.mark.parametrize("p,ok", [("01012345678", True), ("+201512345678", True), ("01312345678", False), ("0101234567", False)])
def test_phone(p, ok):
    assert E.validate_phone(p) is ok


def test_masking_hides_pii():
    assert E.mask_nid("29501120100503") == "2••••••••••503"
    assert "0100" not in E.mask_phone("+201001234567")[6:]
    assert E.mask_iban(E.make_iban(1, 1)).count("•") == 8


# ---------- synthetic data ----------
@pytest.fixture(scope="module")
def small():
    return generate(800, seed=1)


def test_data_quality_all_pass(small):
    dq = dq_checks(small)
    assert (dq.status == "PASS").all(), dq[dq.status != "PASS"]


def test_egyptian_realism(small):
    c = small["customers"]
    assert c.governorate_code.isin(E.GOV_CODES).all()
    assert c.age.between(18, 80).all()
    assert c.phone.str.match(r"^\+201[0125]\d{8}$").all()
    assert small["transactions"].is_fraud.mean() < 0.02          # fraud is rare
    assert set(small["transactions"].direction) == {"debit", "credit"}


# ---------- auth ----------
def test_password_policy():
    assert S.password_issues("weak")
    assert S.password_issues("Secret123") == []


def test_argon2_and_jwt():
    h = S.hash_pw("Secret123")
    assert h.startswith("$argon2") and S.verify_pw(h, "Secret123") and not S.verify_pw(h, "nope")
    tok = S.make_token({"id": 7, "role": "customer", "customer_id": 42})
    assert S.decode(tok)["cid"] == 42
    assert S.decode(tok[:-3] + "abc") is None                    # tampered token rejected


# ---------- suitability ----------
def _fc():
    return {u[0]: {"vol_annual": u[6], "prob_up": 0.55, "exp_ret_5d": 0.004, "confidence": "medium", "last_close": u[5], "mom_3m": 0.05}
            for u in E.UNIVERSE}


@pytest.mark.parametrize("band", [1, 2, 3, 4, 5])
def test_no_suitability_violations(band):
    picks = R.recommend(band, _fc(), set(), False, {})
    assert picks and all(p["vol_annual"] <= R.VOL_CAP[band] for p in picks)
    sectors = [p["sector"] for p in picks]
    assert max(sectors.count(s) for s in sectors) <= 2         # diversification


def test_sharia_filter_and_conservative_no_us():
    picks = R.recommend(1, _fc(), set(), True, {})
    assert all(p["sharia"] for p in picks) and all(p["market"] != "US" for p in picks)


def test_risk_band_capacity_adjustment():
    aggressive = {"horizon": 5, "experience": 5, "drawdown": 5, "goal": 5, "share": 5}
    young = R.risk_band(aggressive, {"age": 30, "sector": "Private", "savings_months": 6, "dti": 0.1})[0]
    retiree = R.risk_band(aggressive, {"age": 70, "sector": "Self-employed", "savings_months": 1, "dti": 0.5})[0]
    assert young == 5 and retiree < young


# ---------- forecasting honesty ----------
def test_forecast_no_leakage(tmp_path, monkeypatch):
    from masar import market_data, ml_forecast
    monkeypatch.setattr(ml_forecast, "MODELS_DIR", tmp_path)      # don't overwrite the real report
    rep = ml_forecast.train(market_data.simulate(seed=3))["report"]
    # on random-walk data an honest model must be ~50%; >60% would mean leakage
    assert 0.40 < rep["mean"]["model_acc"] < 0.60
    assert 0.40 < rep["shuffled_label_acc"] < 0.60


# ---------- fraud ----------
def test_fraud_scorer_separates():
    from masar.ml_fraud import Scorer
    s = Scorer()
    base = {"cust_avg": 500.0, "income": 15000, "home_gov": "Cairo", "channel": "POS"}
    normal = s.score({**base, "amount": 450.0, "hour": 14, "governorate": "Cairo", "new_device": False, "velocity_1h": 1})
    fraud = s.score({**base, "amount": 12000.0, "hour": 3, "governorate": "Aswan", "new_device": True, "velocity_1h": 6, "channel": "InstaPay"})
    assert fraud[0] >= 60 > normal[0] and len(fraud[1]) >= 3
