"""Fraud / anomaly detection: rules + IsolationForest (unsupervised) + LightGBM (supervised on labelled scenarios)."""
from __future__ import annotations

import json

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_score, recall_score

from .config import MODELS_DIR

CHANNELS = ["POS", "E-commerce", "ATM", "InstaPay", "Wallet", "Fawry", "Bank transfer"]
FEATS = ["log_amount", "ratio_avg", "ratio_income", "hour", "is_night", "geo_mismatch", "new_device", "ch_idx", "velocity_1h"]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame(index=df.index)
    x["log_amount"] = np.log1p(df.amount)
    x["ratio_avg"] = df.amount / (df.cust_avg + 1)
    x["ratio_income"] = df.amount / (df.income + 1)
    x["hour"] = df.hour
    x["is_night"] = df.hour.between(0, 5).astype(int)
    x["geo_mismatch"] = (df.governorate != df.home_gov).astype(int)
    x["new_device"] = df.new_device.astype(int)
    x["ch_idx"] = df.channel.map({c: i for i, c in enumerate(CHANNELS)}).fillna(0).astype(int)
    x["velocity_1h"] = df.velocity_1h
    return x


def train(tx: pd.DataFrame, customers: pd.DataFrame) -> dict:
    d = tx[tx.direction == "debit"].copy()
    d["hour"] = d.ts.dt.hour
    avg = d[~d.is_fraud].groupby("customer_id").amount.mean()
    d["cust_avg"] = d.customer_id.map(avg).fillna(d.amount.mean())
    cm = customers.set_index("customer_id")
    d["income"] = d.customer_id.map(cm.monthly_income)
    d["home_gov"] = d.customer_id.map(cm.governorate_en)
    d["hbucket"] = d.ts.dt.floor("h")
    d["velocity_1h"] = d.groupby(["customer_id", "hbucket"]).amount.transform("size")
    pos = d[d.is_fraud]; neg = d[~d.is_fraud].sample(min(400_000, (~d.is_fraud).sum()), random_state=1)
    s = pd.concat([pos, neg]).sample(frac=1, random_state=2)
    X = make_features(s); y = s.is_fraud.astype(int)
    cut = int(len(s) * 0.75)
    normal = X.iloc[:cut][y.iloc[:cut] == 0]
    iso = IsolationForest(n_estimators=200, contamination=0.01, random_state=0).fit(normal.sample(min(150_000, len(normal)), random_state=3))
    gbm = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, verbose=-1, scale_pos_weight=20).fit(X.iloc[:cut], y.iloc[:cut])
    p = gbm.predict_proba(X.iloc[cut:])[:, 1]
    an = -iso.score_samples(X.iloc[cut:])
    yt = y.iloc[cut:]
    rep = {"pr_auc_lightgbm": round(float(average_precision_score(yt, p)), 4),
           "pr_auc_isolation_forest": round(float(average_precision_score(yt, an)), 4),
           "precision_at_0.5": round(float(precision_score(yt, p > 0.5)), 4),
           "recall_at_0.5": round(float(recall_score(yt, p > 0.5)), 4),
           "fraud_rate_in_data": round(float(d.is_fraud.mean()), 5), "n_train": cut, "n_test": len(s) - cut,
           "scenarios": d[d.is_fraud].fraud_scenario.value_counts().to_dict()}
    joblib.dump({"gbm": gbm, "iso": iso, "iso_ref": np.percentile(-iso.score_samples(X.iloc[:cut]), [50, 99])}, MODELS_DIR / "fraud.joblib")
    (MODELS_DIR / "fraud_report.json").write_text(json.dumps(rep, indent=2))
    return rep


class Scorer:
    def __init__(self):
        m = joblib.load(MODELS_DIR / "fraud.joblib")
        self.gbm, self.iso, self.ref = m["gbm"], m["iso"], m["iso_ref"]

    def score(self, tx: dict) -> tuple[int, list[str]]:
        df = pd.DataFrame([tx])
        X = make_features(df)
        p = float(self.gbm.predict_proba(X)[:, 1][0])
        a = float(-self.iso.score_samples(X)[0])
        a_n = float(np.clip((a - self.ref[0]) / (self.ref[1] - self.ref[0] + 1e-9), 0, 1))
        reasons = []
        r = tx["amount"] / (tx["cust_avg"] + 1)
        if r > 5: reasons.append(f"Amount is {r:.0f}x this customer's average")
        if 0 <= tx["hour"] <= 5: reasons.append(f"Night-time transaction ({tx['hour']:02d}:00)")
        if tx["governorate"] != tx["home_gov"]: reasons.append(f"Location {tx['governorate']} differs from home ({tx['home_gov']})")
        if tx["new_device"]: reasons.append("New / unrecognised device")
        if tx["velocity_1h"] >= 5: reasons.append(f"{tx['velocity_1h']} transactions within one hour")
        rules = min(1.0, 0.25 * len(reasons))
        score = int(round(100 * (0.6 * p + 0.25 * a_n + 0.15 * rules)))
        return score, reasons
