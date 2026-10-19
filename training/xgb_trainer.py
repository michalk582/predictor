import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score, mean_absolute_percentage_error
from database.loader import DataLoader, FEATURES

MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "xgb_model.json"
META_PATH = MODEL_DIR / "xgb_model_meta.json"
MODEL_VERSION = "xgb_v2"


class XGBTrainer:
    def __init__(self, model_params: Optional[Dict[str, Any]] = None):
        default_params = {
            "tree_method": "hist",
            "early_stopping_rounds": 50,
            "n_estimators": 2000,
            "learning_rate": 0.05,
            "random_state": 42,
        }
        if model_params:
            default_params.update(model_params)

        self.model = xgb.XGBRegressor(**default_params)
        self.metrics: Dict[str, float] = {}

    def train(self, X_train, y_train, X_val, y_val) -> xgb.XGBRegressor:
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_train, y_train), (X_val, y_val)],
            verbose=100,
        )
        return self.model

    def evaluate(self, X_train, y_train, X_test, y_test) -> Dict[str, float]:
        pred_train = self.model.predict(X_train)
        pred_test = self.model.predict(X_test)

        self.metrics = {
            "train_mae": float(mean_absolute_error(y_train, pred_train)),
            "test_mae": float(mean_absolute_error(y_test, pred_test)),
            "train_r2": float(r2_score(y_train, pred_train)),
            "test_r2": float(r2_score(y_test, pred_test)),
            "train_mape": float(mean_absolute_percentage_error(y_train, pred_train) * 100),
            "test_mape": float(mean_absolute_percentage_error(y_test, pred_test) * 100),
        }

        print(
            f"Test:     MAE {self.metrics['test_mae']:.1f} MW | MAPE {self.metrics['test_mape']:.2f}% | R2 {self.metrics['test_r2']:.4f}")
        print(
            f"Trening:  MAE {self.metrics['train_mae']:.1f} MW | MAPE {self.metrics['train_mape']:.2f}% | R2 {self.metrics['train_r2']:.4f}")
        return self.metrics

    def save_model(self, filepath: str) -> None:
        self.model.save_model(filepath)
        print(f"Zapisano model: {filepath}")

    def save_metadata(self, filepath: str, extra: Dict[str, Any]) -> None:
        meta = {
            "model_version": MODEL_VERSION,
            "trained_at": datetime.now().isoformat(timespec="seconds"),
            "features": list(self.model.get_booster().feature_names),
            "best_iteration": int(self.model.best_iteration),
            "metrics": self.metrics,
            **extra,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"Zapisano metadane: {filepath}")

    def load_model(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Brak modelu: {filepath}")
        self.model.load_model(filepath)
        print(f"Model wczytano z: {filepath}")

    def predict(self, X):
        """Generuje predykcje za pomocą wczytanego modelu."""
        return self.model.predict(X)



if __name__ == "__main__":
    TEST_DAYS = 60
    VAL_DAYS = 30

    loader = DataLoader()
    df = loader.get_data()
    X_train_full, X_test, y_train_full, y_test = loader.prepare_data_to_training(df, test_days=TEST_DAYS)

    val_size = VAL_DAYS * 24
    X_train, X_val = X_train_full.iloc[:-val_size], X_train_full.iloc[-val_size:]
    y_train, y_val = y_train_full.iloc[:-val_size], y_train_full.iloc[-val_size:]

    print(f"Trening: {len(X_train)} | Walidacja: {len(X_val)} | Test: {len(X_test)}")
    print(X_train.head())

    trainer = XGBTrainer()
    trainer.train(X_train, y_train, X_val, y_val)
    trainer.evaluate(X_train, y_train, X_test, y_test)

    trainer.save_model(str(MODEL_PATH))
    trainer.save_metadata(str(META_PATH), extra={
        "train_from": str(df["dtime"].min()),
        "train_to": str(df["dtime"].max()),
        "test_days": TEST_DAYS,
        "val_days": VAL_DAYS,
    })

    assert trainer.model.get_booster().feature_names == FEATURES, "Cechy w modelu nie zgadzają się z FEATURES!"
    print("OK, cechy w modelu:", FEATURES)


