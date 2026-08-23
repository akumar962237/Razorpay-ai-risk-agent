from pathlib import Path
import json
import sqlite3

import joblib
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent

MODEL_PATH = ROOT / "models" / "final_model.joblib"
META_PATH = ROOT / "models" / "model_metadata.json"
DB_PATH = ROOT / "audit.sqlite3"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Payment Risk & Fraud Investigation Agent",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            mode TEXT,
            risk_score INTEGER,
            level TEXT,
            decision TEXT,
            probability REAL,
            reasons TEXT
        )
        """
    )

    conn.commit()
    return conn


# ============================================================
# REQUEST MODELS
# ============================================================

class ContextTransaction(BaseModel):
    """
    Product-context transaction.

    These fields represent merchant/customer context.
    They are separate from the public benchmark features.
    """

    amount: float = Field(ge=0)
    hour: int = Field(ge=0, le=23)

    customer_avg_amount: float = Field(ge=0)

    transactions_24h: int = Field(ge=0)

    account_age_days: int = Field(ge=0)

    new_device: bool = False
    new_location: bool = False

    # Optional real benchmark features.
    # When supplied, the actual trained ML model
    # generates the fraud probability.
    v: list[float] | None = Field(
        default=None,
        min_length=28,
        max_length=28,
    )


class BenchmarkTransaction(BaseModel):
    """
    Public benchmark transaction.

    Expected features:
        Time
        Amount
        V1 ... V28
    """

    time: float = Field(ge=0)
    amount: float = Field(ge=0)

    v: list[float] = Field(
        min_length=28,
        max_length=28,
    )


# ============================================================
# MODEL LOADING
# ============================================================

def load_model_bundle():
    """
    Load the complete serialized model bundle.

    final_model.joblib contains:
        model
        threshold
        features
    """

    if not MODEL_PATH.exists():
        return None

    return joblib.load(MODEL_PATH)


def load_model():
    """
    Extract the actual estimator from the serialized bundle.
    """

    bundle = load_model_bundle()

    if bundle is None:
        return None

    if isinstance(bundle, dict) and "model" in bundle:
        return bundle["model"]

    # Fallback in case a raw estimator is ever saved.
    return bundle


def load_metadata():
    if not META_PATH.exists():
        return None

    try:
        return json.loads(
            META_PATH.read_text()
        )
    except Exception:
        return None


def get_threshold():
    """
    Get the threshold used by the trained model.

    The authoritative value is stored inside
    final_model.joblib.
    """

    bundle = load_model_bundle()

    if isinstance(bundle, dict):
        threshold = bundle.get("threshold")

        if threshold is not None:
            return float(threshold)

    metadata = load_metadata()

    if isinstance(metadata, dict):
        threshold = metadata.get(
            "threshold",
            metadata.get(
                "selected_threshold"
            ),
        )

        if threshold is not None:
            return float(threshold)

    # Safe fallback.
    return 0.95


# ============================================================
# ML PREDICTION
# ============================================================

def predict_probability(
    time_value,
    amount,
    v,
):
    """
    Run the real trained benchmark model.

    Feature order:

        Time, Amount, V1 ... V28
    """

    model = load_model()

    if model is None:
        raise RuntimeError(
            "Benchmark model not found. "
            "Run: python -m backend.ml.pipeline "
            "--data data/raw/creditcard.csv"
        )

    features = np.array(
        [[
            float(time_value),
            float(amount),
            *[float(value) for value in v],
        ]],
        dtype=float,
    )

    probability = float(
        model.predict_proba(features)[0, 1]
    )

    return probability


# ============================================================
# CONTEXT RISK SIGNALS
# ============================================================

def calculate_context_risk(
    transaction: ContextTransaction,
):
    """
    Calculate product-side contextual risk.

    Maximum score = 100.

    IMPORTANT:
    This score is NOT a probability.
    """

    points = 0
    reasons = []

    # --------------------------------------------------------
    # Amount anomaly
    # --------------------------------------------------------

    if transaction.customer_avg_amount > 0:

        ratio = (
            transaction.amount
            / transaction.customer_avg_amount
        )

        if ratio >= 8:

            points += 35

            reasons.append(
                f"Amount is {ratio:.1f}× "
                "the customer's average."
            )

        elif ratio >= 3:

            points += 18

            reasons.append(
              f"Amount is {ratio:.1f}x the customer's average."
            )

    # --------------------------------------------------------
    # New device
    # --------------------------------------------------------

    if transaction.new_device:

        points += 20

        reasons.append(
            "New device detected."
        )

    # --------------------------------------------------------
    # New location
    # --------------------------------------------------------

    if transaction.new_location:

        points += 20

        reasons.append(
            "New transaction location detected."
        )

    # --------------------------------------------------------
    # Late-night transaction
    # --------------------------------------------------------

    if transaction.hour in {
        0,
        1,
        2,
        3,
        4,
        5,
    }:

        points += 10

        reasons.append(
            "Transaction occurred in "
            "a late-night window."
        )

    # --------------------------------------------------------
    # Transaction velocity
    # --------------------------------------------------------

    if transaction.transactions_24h >= 6:

        points += 15

        reasons.append(
            f"High transaction velocity: "
            f"{transaction.transactions_24h} "
            "transactions in 24 hours."
        )

    elif transaction.transactions_24h >= 4:

        points += 8

        reasons.append(
            f"Elevated transaction velocity: "
            f"{transaction.transactions_24h} "
            "transactions in 24 hours."
        )

    # --------------------------------------------------------
    # Account age
    # --------------------------------------------------------

    if transaction.account_age_days < 30:

        points += 10

        reasons.append(
            "Account is less than 30 days old."
        )

    return min(100, points), reasons


# ============================================================
# FINAL RISK POLICY
# ============================================================

def combine_risk(
    ml_probability,
    context_score,
):
    """
    Combine the ML probability and contextual risk.

    Policy:

        70% ML signal
        30% contextual signal

    The resulting risk_score is a bounded risk score,
    NOT a probability.
    """

    ml_score = ml_probability * 100

    final_score = round(
        (
            0.70 * ml_score
            +
            0.30 * context_score
        )
    )

    final_score = max(
        0,
        min(100, final_score),
    )

    # --------------------------------------------------------
    # Decision thresholds
    # --------------------------------------------------------

    if final_score >= 85:

        level = "HIGH"
        decision = "BLOCK"

        action = (
            "Block automatically and create "
            "a high-priority risk case."
        )

    elif final_score >= 55:

        level = "MEDIUM"
        decision = "REVIEW"

        action = (
            "Send for manual review "
            "before fulfillment."
        )

    else:

        level = "LOW"
        decision = "APPROVE"

        action = (
            "Approve and continue monitoring."
        )

    return (
        final_score,
        level,
        decision,
        action,
    )


# ============================================================
# EXPLANATION
# ============================================================

def build_reasons(
    ml_probability,
    context_reasons,
    context_score,
):
    reasons = []

    # Real ML evidence
    reasons.append(
        "Benchmark ML model probability: "
        f"{ml_probability:.1%}."
    )

    # Product-context evidence
    if context_reasons:

        reasons.extend(
            context_reasons
        )

    else:

        reasons.append(
            "No strong product-context "
            "risk signals were triggered."
        )

    reasons.append(
        "Product-context risk score: "
        f"{context_score}/100."
    )

    return reasons


# ============================================================
# AUDIT LOGGING
# ============================================================

def log_result(
    mode,
    result,
):
    conn = db()

    conn.execute(
        """
        INSERT INTO investigations
        (
            mode,
            risk_score,
            level,
            decision,
            probability,
            reasons
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            mode,
            result["risk_score"],
            result["risk_level"],
            result["decision"],
            result["ml_probability"],
            json.dumps(
                result["reasons"]
            ),
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    bundle = load_model_bundle()

    return {
        "status": "ok",
        "benchmark_model_available": (
            MODEL_PATH.exists()
        ),
        "model_bundle_valid": (
            isinstance(bundle, dict)
            and "model" in bundle
        ),
        "selected_threshold": (
            get_threshold()
            if bundle is not None
            else None
        ),
        "metadata": load_metadata(),
    }


# ============================================================
# BENCHMARK PREDICTION
# ============================================================

@app.post("/predict/benchmark")
def predict_benchmark(
    transaction: BenchmarkTransaction,
):

    if not MODEL_PATH.exists():

        return {
            "error": "Benchmark model not trained.",
            "run": (
                "python -m backend.ml.pipeline "
                "--data data/raw/creditcard.csv"
            ),
        }

    # --------------------------------------------------------
    # Real model prediction
    # --------------------------------------------------------

    probability = predict_probability(
        time_value=transaction.time,
        amount=transaction.amount,
        v=transaction.v,
    )

    threshold = get_threshold()

    # --------------------------------------------------------
    # Benchmark-only policy
    # --------------------------------------------------------

    if probability >= threshold:

        decision = "BLOCK"
        level = "HIGH"

        action = (
            "Block automatically and create "
            "a high-priority risk case."
        )

    elif probability >= (
        threshold * 0.55
    ):

        decision = "REVIEW"
        level = "MEDIUM"

        action = (
            "Send for manual review "
            "before fulfillment."
        )

    else:

        decision = "APPROVE"
        level = "LOW"

        action = (
            "Approve and continue monitoring."
        )

    reasons = [
        (
            "Benchmark ML model probability: "
            f"{probability:.1%}."
        ),
        (
            "Selected validation threshold: "
            f"{threshold:.3f}."
        ),
    ]

    result = {
        "risk_score": round(
            probability * 100
        ),

        "risk_level": level,

        "decision": decision,

        "ml_probability": round(
            probability,
            6,
        ),

        "context_risk_score": None,

        "reasons": reasons,

        "recommended_action": action,

        "signals": {
            "amount": transaction.amount,
            "time": transaction.time,
        },
    }

    log_result(
        "benchmark",
        result,
    )

    return result


# ============================================================
# CONTEXT + REAL ML INVESTIGATION
# ============================================================

@app.post("/predict/context")
def predict_context(
    transaction: ContextTransaction,
):

    # --------------------------------------------------------
    # Benchmark features are required for real ML probability
    # --------------------------------------------------------

    if transaction.v is None:

        return {
            "error": (
                "Benchmark features V1-V28 "
                "are required for real ML inference."
            ),

            "message": (
                "Product-context signals can be "
                "calculated separately, but the real "
                "benchmark model requires V1-V28."
            ),
        }

    # --------------------------------------------------------
    # REAL ML MODEL
    # --------------------------------------------------------

    ml_probability = predict_probability(
        time_value=float(
            transaction.hour
        ),

        amount=float(
            transaction.amount
        ),

        v=transaction.v,
    )

    # --------------------------------------------------------
    # PRODUCT CONTEXT
    # --------------------------------------------------------

    context_score, context_reasons = (
        calculate_context_risk(
            transaction
        )
    )

    # --------------------------------------------------------
    # FINAL RISK
    # --------------------------------------------------------

    (
        risk_score,
        level,
        decision,
        action,
    ) = combine_risk(
        ml_probability,
        context_score,
    )

    # --------------------------------------------------------
    # EXPLANATION
    # --------------------------------------------------------

    reasons = build_reasons(
        ml_probability,
        context_reasons,
        context_score,
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = {

        "risk_score": risk_score,

        "risk_level": level,

        "decision": decision,

        # REAL probability from ML model
        "ml_probability": round(
            ml_probability,
            6,
        ),

        # NOT a probability
        "context_risk_score": (
            context_score
        ),

        "reasons": reasons,

        "recommended_action": action,

        "signals": {

            "amount": (
                transaction.amount
            ),

            "customer_average_amount": (
                transaction.customer_avg_amount
            ),

            "transactions_24h": (
                transaction.transactions_24h
            ),

            "account_age_days": (
                transaction.account_age_days
            ),

            "new_device": (
                transaction.new_device
            ),

            "new_location": (
                transaction.new_location
            ),

            "hour": (
                transaction.hour
            ),
        },

        "policy": {

            "ml_weight": 0.70,

            "context_weight": 0.30,

            "block_threshold": 85,

            "review_threshold": 55,
        },
    }

    log_result(
        "context",
        result,
    )

    return result


# ============================================================
# INVESTIGATION HISTORY
# ============================================================

@app.get("/investigations")
def investigations(
    limit: int = 20,
):

    limit = max(
        1,
        min(
            limit,
            100,
        ),
    )

    conn = db()

    rows = conn.execute(
        """
        SELECT
            id,
            created_at,
            mode,
            risk_score,
            level,
            decision,
            probability,
            reasons
        FROM investigations
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return [
        {
            "id": row[0],

            "created_at": row[1],

            "mode": row[2],

            "risk_score": row[3],

            "level": row[4],

            "decision": row[5],

            "probability": row[6],

            "reasons": json.loads(
                row[7]
            ),
        }

        for row in rows
    ]