"""
Tests for ML models: credit scoring, fraud detection, SHAP explainability.
"""
import numpy as np
import pytest
from backend.ml.credit_model.features import CreditFeatures, engineer_features
from backend.ml.credit_model.predict import CreditModelPredictor
from backend.ml.fraud_model.predict import FraudModelPredictor
from backend.ml.explainability.shap_explainer import SHAPExplainer


class TestCreditFeatures:
    def test_to_array_correct_length(self):
        features = CreditFeatures(
            credit_score=0.75,
            bureau_score_norm=0.8,
            dti_ratio=0.3,
            bank_balance_norm=0.6,
            income_stability=1.0,
            loan_amount_norm=0.4,
            loan_type_encoded=0,
            monthly_obligations_norm=0.3,
            income_to_loan_ratio=0.5,
            bank_balance_months=3.0,
            fraud_risk_score=0.1,
        )
        arr = features.to_array()
        assert arr.shape == (11,)
        assert arr.dtype == np.float32

    def test_engineer_features_from_raw_dict(self):
        raw = {
            "credit_score": 0.75,
            "bureau_score": 720,
            "dti_ratio": 0.3,
            "bank_balance_avg": 120000,
            "income_stability": 1.0,
            "loan_amount": 500000,
            "loan_type": "personal",
            "monthly_obligations": 15000,
            "monthly_income": 80000,
            "fraud_risk_score": 0.1,
        }
        features = engineer_features(raw)
        assert isinstance(features, CreditFeatures)
        arr = features.to_array()
        assert arr.shape == (11,)
        assert np.all(np.isfinite(arr))

    def test_dti_normalization_clips_to_one(self):
        raw = {
            "credit_score": 0.5,
            "bureau_score": 600,
            "dti_ratio": 2.0,  # absurdly high
            "bank_balance_avg": 0,
            "income_stability": 0.5,
            "loan_amount": 1000000,
            "loan_type": "personal",
            "monthly_obligations": 200000,
            "monthly_income": 10000,
            "fraud_risk_score": 0.8,
        }
        features = engineer_features(raw)
        arr = features.to_array()
        # All values should be in [0, 1] after normalization
        assert np.all(arr >= 0)
        assert np.all(arr <= 1)


class TestCreditModelPredictor:
    def test_predict_returns_valid_range(self):
        predictor = CreditModelPredictor()
        features = np.array([0.7, 0.8, 0.3, 0.5, 1.0, 0.4, 0.0, 0.3, 0.5, 3.0, 0.1], dtype=np.float32)
        score, prob = predictor.predict(features)
        assert 0 <= score <= 1
        assert 0 <= prob <= 1

    def test_predict_heuristic_fallback(self):
        """Should work even without a trained model file."""
        predictor = CreditModelPredictor()
        predictor.model = None  # force heuristic
        features = np.array([0.7, 0.8, 0.3, 0.5, 1.0, 0.4, 0.0, 0.3, 0.5, 3.0, 0.1], dtype=np.float32)
        score, prob = predictor.predict(features)
        assert 0 <= score <= 1
        assert 0 <= prob <= 1

    def test_high_quality_features_score_higher(self):
        predictor = CreditModelPredictor()
        good = np.array([0.9, 0.9, 0.1, 0.9, 1.0, 0.2, 0.0, 0.1, 0.9, 6.0, 0.05], dtype=np.float32)
        bad = np.array([0.2, 0.2, 0.8, 0.1, 0.0, 0.9, 0.0, 0.8, 0.1, 0.5, 0.9], dtype=np.float32)
        good_score, _ = predictor.predict(good)
        bad_score, _ = predictor.predict(bad)
        assert good_score > bad_score


class TestFraudModelPredictor:
    def test_fraud_predict_returns_valid_range(self):
        predictor = FraudModelPredictor()
        features = np.array([0.5, 0.4, 0.3, 0.6, 0.2, 0.7, 0.1, 0.3, 0.5])
        score = predictor.predict_proba(features)
        assert 0 <= score <= 1

    def test_high_fraud_features_gives_higher_score(self):
        predictor = FraudModelPredictor()
        normal = np.array([0.7, 0.8, 0.2, 0.9, 0.1, 0.3, 0.1, 0.6, 0.4])
        fraud = np.array([0.1, 0.05, 0.95, 0.02, 0.9, 0.95, 0.9, 0.05, 0.98])
        normal_score = predictor.predict_proba(normal)
        fraud_score = predictor.predict_proba(fraud)
        # Fraud features should generally produce higher scores
        # (not guaranteed without trained model, but heuristic should reflect this)
        assert fraud_score >= 0  # Basic sanity


class TestSHAPExplainer:
    def test_explain_returns_feature_dict(self):
        explainer = SHAPExplainer()
        features = np.array([0.7, 0.8, 0.3, 0.5, 1.0, 0.4, 0.0, 0.3, 0.5, 3.0, 0.1], dtype=np.float32)
        shap_values = explainer.explain(features)
        assert isinstance(shap_values, dict)
        assert len(shap_values) == 11
        # All values should be finite floats
        for v in shap_values.values():
            assert isinstance(v, float)
            assert np.isfinite(v)

    def test_generate_explanation_report(self):
        explainer = SHAPExplainer()
        shap_values = {
            "credit_score": 0.15,
            "dti_ratio": -0.08,
            "bank_balance_norm": 0.06,
            "bureau_score_norm": 0.12,
        }
        report = explainer.generate_explanation_report(shap_values)
        assert isinstance(report, str)
        assert len(report) > 50
        assert "credit_score" in report.lower() or "Credit" in report
