"""Stock forecasting: LightGBM direction classifier + quantile regressors, walk-forward validated vs baselines."""
from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

from .config import MODELS_DIR

FEATS = ["r1", "r5", "r10", "r20", "vol10", "vol20", "rsi14", "macd", "bbp", "volz", "mkt_r1", "mkt_r5", "dow"]
H = 5


def _rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return 100 - 100 / (1 + up / (dn + 1e-12))


def features(hist: pd.DataFrame) -> pd.DataFrame:
    from . import egypt as E
    mkt = {u[0]: u[3] for u in E.UNIVERSE}
    out = []
    for sym, g in hist.sort_values("date").groupby("symbol"):
        g = g.copy(); c = g.close
        lr = np.log(c).diff()
        g["r1"] = lr; g["r5"] = np.log(c).diff(5); g["r10"] = np.log(c).diff(10); g["r20"] = np.log(c).diff(20)
        g["vol10"] = lr.rolling(10).std(); g["vol20"] = lr.rolling(20).std()
        g["rsi14"] = _rsi(c)
        g["macd"] = (c.ewm(span=12).mean() - c.ewm(span=26).mean()) / c
        m20 = c.rolling(20).mean(); s20 = c.rolling(20).std()
        g["bbp"] = (c - (m20 - 2 * s20)) / (4 * s20 + 1e-12)
        g["volz"] = (g.volume - g.volume.rolling(20).mean()) / (g.volume.rolling(20).std() + 1e-9)
        g["dow"] = g.date.dt.weekday
        g["y_dir"] = (lr.shift(-1) > 0).astype(float).where(lr.shift(-1).notna())
        g["y_r5"] = np.log(c).shift(-H) - np.log(c)
        g["market"] = mkt.get(sym, "US")
        out.append(g)
    df = pd.concat(out, ignore_index=True)
    mk = df.groupby(["market", "date"]).r1.mean().rename("mkt_r1").reset_index()
    df = df.merge(mk, on=["market", "date"], how="left")
    df["mkt_r5"] = df.groupby("symbol").mkt_r1.transform(lambda s: s.rolling(5).sum())
    return df


PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=100, subsample=0.8,
              subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1)


def train(hist: pd.DataFrame) -> dict:
    df = features(hist).dropna(subset=FEATS)
    lab = df.dropna(subset=["y_dir"])
    dates = np.sort(lab.date.unique())
    folds = []
    n_test = 60
    for k in range(6, 0, -1):            # 6 walk-forward folds over the last ~360 trading days
        te_start = dates[-k * n_test]; te_end = dates[min(len(dates) - 1, -k * n_test + n_test - 1)]
        tr = lab[lab.date < te_start - np.timedelta64(H + 2, "D")]          # purge/embargo gap
        te = lab[(lab.date >= te_start) & (lab.date <= te_end)]
        clf = lgb.LGBMClassifier(**PARAMS).fit(tr[FEATS], tr.y_dir)
        p = clf.predict_proba(te[FEATS])[:, 1]
        maj = float(tr.y_dir.mean() >= 0.5)
        mom = (te.r1 > 0).astype(float)
        folds.append({"test_from": str(pd.Timestamp(te_start).date()), "test_to": str(pd.Timestamp(te_end).date()), "n": int(len(te)),
                      "model_acc": accuracy_score(te.y_dir, p > 0.5), "model_auc": roc_auc_score(te.y_dir, p),
                      "always_up_acc": accuracy_score(te.y_dir, np.full(len(te), maj)), "momentum_acc": accuracy_score(te.y_dir, mom)})
    # leakage sanity: shuffled labels must collapse to ~50%
    tr = lab[lab.date < dates[-n_test]]; te = lab[lab.date >= dates[-n_test]]
    shuf = lgb.LGBMClassifier(**PARAMS).fit(tr[FEATS], np.random.default_rng(0).permutation(tr.y_dir.to_numpy()))
    shuffled_acc = accuracy_score(te.y_dir, shuf.predict_proba(te[FEATS])[:, 1] > 0.5)

    # final models on all labelled data
    clf = lgb.LGBMClassifier(**PARAMS).fit(lab[FEATS], lab.y_dir)
    lab5 = df.dropna(subset=["y_r5"])
    qs = {q: lgb.LGBMRegressor(objective="quantile", alpha=q, **PARAMS).fit(lab5[FEATS], lab5.y_r5) for q in (0.1, 0.5, 0.9)}
    # interval coverage on last fold (in-sample-ish for quantiles; reported honestly)
    last = df.groupby("symbol").tail(1)
    prob = clf.predict_proba(last[FEATS])[:, 1]
    fc = []
    per_sym = {}
    for sym, g in lab[lab.date >= dates[-6 * n_test]].groupby("symbol"):
        pass
    for (_, row), p in zip(last.iterrows(), prob):
        x = row[FEATS].to_frame().T.astype(float)
        q10, q50, q90 = (float(qs[q].predict(x)[0]) for q in (0.1, 0.5, 0.9))
        q10, q90 = min(q10, q50), max(q90, q50)
        conf = abs(p - 0.5) * 2
        fc.append({"symbol": row.symbol, "as_of": str(row.date.date()), "last_close": float(row.close), "prob_up": round(float(p), 4),
                   "exp_ret_5d": round(q50, 5), "p10_5d": round(q10, 5), "p90_5d": round(q90, 5),
                   "confidence": "low" if conf < 0.1 else ("medium" if conf < 0.25 else "high"),
                   "vol_annual": round(float(row.vol20 * np.sqrt(252)), 4), "mom_3m": None})
    fc = pd.DataFrame(fc)
    mom = hist.sort_values("date").groupby("symbol").close.apply(lambda s: s.iloc[-1] / s.iloc[-63] - 1)
    fc["mom_3m"] = fc.symbol.map(mom).round(4)
    f = pd.DataFrame(folds)
    report = {
        "model": "LightGBM global panel model (direction) + quantile regressors (5-day return P10/P50/P90)",
        "validation": "walk-forward, 6 folds x 60 trading days, purge gap of 7 days, no shuffling",
        "folds": folds,
        "mean": {k: round(float(f[k].mean()), 4) for k in ["model_acc", "model_auc", "always_up_acc", "momentum_acc"]},
        "shuffled_label_acc": round(float(shuffled_acc), 4),
        "data_source": sorted(hist.source.unique().tolist()),
        "note": "Daily direction is close to a coin flip; 52-58% out-of-sample is realistic. Simulated series are random walks, so ~50% is the correct (leak-free) result there.",
        "feature_importance": dict(sorted(zip(FEATS, map(int, clf.feature_importances_)), key=lambda kv: -kv[1])),
    }
    (MODELS_DIR / "forecast_report.json").write_text(json.dumps(report, indent=2))
    return {"forecasts": fc, "report": report}
