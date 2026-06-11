"""
MediAid — AI Risk Predictor
SDG 3: Good Health and Well-Being

Trains and exports an interpretable health risk model.
Uses scikit-learn with a Rule-Based + ML hybrid approach
for maximum transparency and clinical safety.

Usage:
    python risk_predictor.py --train    # Train on synthetic data
    python risk_predictor.py --predict  # Interactive prediction
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline
import joblib
import argparse
import json
from pathlib import Path


# ── SYNTHETIC DATASET GENERATOR ───────────────────────────────────
def generate_synthetic_dataset(n=5000, seed=42):
    """
    Generate realistic synthetic health data for model training.
    Features are based on WHO risk factor guidelines.
    """
    rng = np.random.default_rng(seed)
    
    age = rng.integers(18, 80, n)
    gender = rng.choice([0, 1], n)  # 0=female, 1=male
    bmi = rng.normal(26, 5, n).clip(14, 50)
    systolic_bp = rng.normal(120, 18, n).clip(80, 220)
    blood_glucose = rng.normal(95, 22, n).clip(60, 400)
    smoker = rng.choice([0, 1], n, p=[0.7, 0.3])
    physical_activity = rng.choice([0, 1, 2], n, p=[0.3, 0.5, 0.2])  # 0=low,1=mod,2=high
    family_history_diabetes = rng.choice([0, 1], n, p=[0.7, 0.3])
    family_history_heart = rng.choice([0, 1], n, p=[0.8, 0.2])
    cholesterol = rng.normal(190, 35, n).clip(100, 350)
    
    # Diabetes risk label (rule-based ground truth)
    p_diabetes = (
        0.001 * (age - 18) +
        0.02 * (bmi - 22).clip(0) +
        0.003 * (blood_glucose - 90).clip(0) +
        0.15 * family_history_diabetes +
        0.10 * (physical_activity == 0) +
        rng.normal(0, 0.05, n)
    ).clip(0, 1)
    diabetes = (rng.random(n) < p_diabetes).astype(int)
    
    # Hypertension risk label
    p_hyp = (
        0.008 * (systolic_bp - 110).clip(0) +
        0.001 * (age - 18) +
        0.12 * smoker +
        0.008 * (bmi - 22).clip(0) +
        rng.normal(0, 0.05, n)
    ).clip(0, 1)
    hypertension = (rng.random(n) < p_hyp).astype(int)
    
    df = pd.DataFrame({
        "age": age, "gender": gender, "bmi": bmi,
        "systolic_bp": systolic_bp, "blood_glucose": blood_glucose,
        "smoker": smoker, "physical_activity": physical_activity,
        "family_history_diabetes": family_history_diabetes,
        "family_history_heart": family_history_heart,
        "cholesterol": cholesterol,
        "diabetes": diabetes, "hypertension": hypertension,
    })
    
    print(f"Dataset: {n} samples | Diabetes prevalence: {diabetes.mean():.1%} | Hypertension: {hypertension.mean():.1%}")
    return df


FEATURES = [
    "age", "gender", "bmi", "systolic_bp", "blood_glucose",
    "smoker", "physical_activity", "family_history_diabetes",
    "family_history_heart", "cholesterol"
]


def train_models(output_dir: Path):
    """Train diabetes and hypertension risk models."""
    print("🧠 Training MediAid Risk Prediction Models...\n")
    output_dir.mkdir(exist_ok=True)
    
    df = generate_synthetic_dataset(n=10000)
    X = df[FEATURES]
    
    results = {}
    
    for target in ["diabetes", "hypertension"]:
        print(f"── Training {target.upper()} model ──")
        y = df[target]
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
            )),
        ])
        
        pipeline.fit(X_train, y_train)
        
        # Evaluation
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")
        
        print(classification_report(y_test, y_pred))
        print(f"Test AUC: {auc:.3f} | CV AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}\n")
        
        # Feature importance
        importances = dict(zip(
            FEATURES,
            pipeline.named_steps["model"].feature_importances_.tolist()
        ))
        
        # Save model
        model_path = output_dir / f"{target}_model.pkl"
        joblib.dump(pipeline, model_path)
        
        results[target] = {
            "auc": round(auc, 4),
            "cv_auc_mean": round(cv_scores.mean(), 4),
            "feature_importances": {k: round(v, 4) for k, v in importances.items()},
            "model_path": str(model_path),
        }
        
        print(f"✅ Model saved: {model_path}")
    
    # Save metadata
    meta_path = output_dir / "model_metadata.json"
    with open(meta_path, "w") as f:
        json.dump({
            "version": "1.0.0",
            "features": FEATURES,
            "targets": list(results.keys()),
            "models": results,
        }, f, indent=2)
    
    print(f"\n📊 Metadata saved: {meta_path}")
    return results


def predict_risk(models_dir: Path, patient_data: dict) -> dict:
    """
    Predict health risks for a single patient.
    
    patient_data keys: age, gender (0/1), bmi, systolic_bp,
    blood_glucose, smoker (0/1), physical_activity (0/1/2),
    family_history_diabetes (0/1), family_history_heart (0/1),
    cholesterol
    """
    row = pd.DataFrame([{f: patient_data.get(f, 0) for f in FEATURES}])
    results = {}
    
    for target in ["diabetes", "hypertension"]:
        model_path = models_dir / f"{target}_model.pkl"
        if model_path.exists():
            pipeline = joblib.load(model_path)
            prob = pipeline.predict_proba(row)[0, 1]
            results[target] = {
                "risk_score": round(float(prob), 4),
                "risk_level": "low" if prob < 0.25 else "moderate" if prob < 0.55 else "high" if prob < 0.80 else "critical"
            }
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MediAid Risk Predictor")
    parser.add_argument("--train", action="store_true", help="Train models")
    parser.add_argument("--predict", action="store_true", help="Interactive prediction")
    parser.add_argument("--output", default="./models", help="Model output directory")
    args = parser.parse_args()
    
    models_dir = Path(args.output)
    
    if args.train:
        train_models(models_dir)
    
    elif args.predict:
        print("MediAid Risk Assessment — Interactive Mode\n")
        patient = {
            "age": int(input("Age: ")),
            "gender": int(input("Gender (0=female, 1=male): ")),
            "bmi": float(input("BMI: ")),
            "systolic_bp": float(input("Systolic BP: ")),
            "blood_glucose": float(input("Blood glucose (mg/dL): ")),
            "smoker": int(input("Smoker (0=no, 1=yes): ")),
            "physical_activity": int(input("Physical activity (0=low, 1=moderate, 2=high): ")),
            "family_history_diabetes": int(input("Family history of diabetes (0/1): ")),
            "family_history_heart": int(input("Family history of heart disease (0/1): ")),
            "cholesterol": float(input("Total cholesterol (mg/dL, default 190): ") or "190"),
        }
        
        risks = predict_risk(models_dir, patient)
        print("\n── Risk Assessment Results ──")
        for condition, data in risks.items():
            print(f"{condition.capitalize()}: {data['risk_score']*100:.1f}% ({data['risk_level'].upper()})")
    
    else:
        parser.print_help()
