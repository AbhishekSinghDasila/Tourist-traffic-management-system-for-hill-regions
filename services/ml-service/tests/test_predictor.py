from unittest.mock import MagicMock, patch
import pytest
from app.services.predictor import XGBoostPredictor, FEATURE_COLUMNS, DISTRICTS


def test_prediction_requires_loaded_model():
    with pytest.raises(RuntimeError):
        XGBoostPredictor().predict("nainital", 5, 6, 1, 0, 1, 0, 7)


@pytest.mark.parametrize("fraction,risk", [(0, "GREEN"), (.6, "AMBER"), (.85, "RED"), (2, "RED")])
def test_prediction_capacity_and_risk(fraction, risk):
    p = XGBoostPredictor()
    p._ready = True
    p._encoder = MagicMock()
    p._encoder.transform.return_value = [0]
    p._model = MagicMock()
    p._model.predict.return_value = [DISTRICTS["nainital"] * fraction]
    result = p.predict("nainital", 5, 6, 1, 0, 1, 0, 7)
    assert result["risk_level"] == risk
    assert 0 <= result["capacity_pct"] <= 100
    assert list(p._model.predict.call_args.args[0].columns) == FEATURE_COLUMNS


def test_incompatible_feature_artifact_is_rejected():
    p = XGBoostPredictor()
    with patch("os.path.exists", return_value=True), patch(
        "joblib.load", side_effect=[MagicMock(), MagicMock(), ["wrong_feature"]]
    ):
        assert p.load() is False
        assert not p.is_ready
