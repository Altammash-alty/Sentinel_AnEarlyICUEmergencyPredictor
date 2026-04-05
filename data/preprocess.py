"""
SENTINEL — Data Preprocessing Pipeline
Loads generated CSV data, normalizes vitals, reshapes into LSTM tensors,
splits into train/val/test sets, and saves scaler + numpy arrays.
"""

import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "generated")
ML_DIR        = os.path.join(BASE_DIR, "..", "ml")
SAVED_DIR     = os.path.join(ML_DIR, "saved_model")
PROCESSED_DIR = os.path.join(ML_DIR, "processed")

os.makedirs(SAVED_DIR,     exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

SEQ_CSV   = os.path.join(DATA_DIR, "patient_sequences.csv")
LABEL_CSV = os.path.join(DATA_DIR, "training_labels.csv")
SCALER_PATH = os.path.join(SAVED_DIR, "scaler.pkl")

VITAL_COLS = ["HR", "BP_sys", "SpO2", "RR", "Temp"]
N_STEPS    = 60

TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
# TEST = remaining 0.15

RANDOM_SEED = 42


# ──────────────────────────────────────────────────────────────────────────────
# Load
# ──────────────────────────────────────────────────────────────────────────────

def load_data() -> tuple[np.ndarray, np.ndarray]:
    """
    Load sequences and labels.
    Returns:
        X : (N, 60, 5)  — raw (unscaled) vital sequences
        y : (N,)        — integer labels 0/1/2
    """
    print("Loading sequences CSV ...")
    seq_df   = pd.read_csv(SEQ_CSV)
    label_df = pd.read_csv(LABEL_CSV)

    n_sequences = seq_df["seq_id"].nunique()
    print(f"  Found {n_sequences} sequences with {N_STEPS} steps each.")

    # Sort to ensure correct step ordering
    seq_df = seq_df.sort_values(["seq_id", "step"])

    # Build 3-D array
    X = seq_df[VITAL_COLS].values.reshape(n_sequences, N_STEPS, len(VITAL_COLS))
    y = label_df.sort_values("seq_id")["label"].values

    print(f"  X shape : {X.shape}")
    print(f"  y shape : {y.shape}")
    print(f"  Label distribution: {dict(zip(*np.unique(y, return_counts=True)))}")
    return X, y


# ──────────────────────────────────────────────────────────────────────────────
# Split
# ──────────────────────────────────────────────────────────────────────────────

def split_data(X: np.ndarray, y: np.ndarray):
    """
    Stratified 70/15/15 split.
    Returns train, val, test splits.
    """
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y,
        test_size=(1.0 - TRAIN_RATIO - VAL_RATIO),
        stratify=y,
        random_state=RANDOM_SEED,
    )

    val_fraction_of_trainval = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)

    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=val_fraction_of_trainval,
        stratify=y_trainval,
        random_state=RANDOM_SEED,
    )

    print(f"\nSplit sizes:")
    print(f"  Train : {len(X_train):,}  ({len(X_train)/len(X)*100:.1f}%)")
    print(f"  Val   : {len(X_val):,}   ({len(X_val)/len(X)*100:.1f}%)")
    print(f"  Test  : {len(X_test):,}   ({len(X_test)/len(X)*100:.1f}%)")

    return X_train, X_val, X_test, y_train, y_val, y_test


# ──────────────────────────────────────────────────────────────────────────────
# Normalize
# ──────────────────────────────────────────────────────────────────────────────

def normalize(X_train, X_val, X_test):
    """
    Fit MinMaxScaler on training data only.
    Transform all three splits using the same fitted scaler.
    """
    N_train, T, F = X_train.shape

    # Reshape to 2-D for scaler: (N*T, F)
    X_train_2d = X_train.reshape(-1, F)
    X_val_2d   = X_val.reshape(-1, F)
    X_test_2d  = X_test.reshape(-1, F)

    scaler = MinMaxScaler()
    X_train_scaled = scaler.fit_transform(X_train_2d)
    X_val_scaled   = scaler.transform(X_val_2d)
    X_test_scaled  = scaler.transform(X_test_2d)

    # Reshape back to 3-D
    X_train_scaled = X_train_scaled.reshape(N_train, T, F)
    X_val_scaled   = X_val_scaled.reshape(len(X_val), T, F)
    X_test_scaled  = X_test_scaled.reshape(len(X_test), T, F)

    # Save scaler
    joblib.dump(scaler, SCALER_PATH)
    print(f"\n✓ Scaler saved → {SCALER_PATH}")

    return X_train_scaled, X_val_scaled, X_test_scaled, scaler


# ──────────────────────────────────────────────────────────────────────────────
# Save tensors
# ──────────────────────────────────────────────────────────────────────────────

def save_tensors(X_train, X_val, X_test, y_train, y_val, y_test):
    arrays = {
        "X_train": X_train, "X_val": X_val, "X_test": X_test,
        "y_train": y_train, "y_val": y_val, "y_test": y_test,
    }
    for name, arr in arrays.items():
        path = os.path.join(PROCESSED_DIR, f"{name}.npy")
        np.save(path, arr)
        print(f"  Saved {name}.npy  shape={arr.shape}")

    print(f"\n✓ All tensors saved to {PROCESSED_DIR}/")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("SENTINEL — Preprocessing Pipeline")
    print("=" * 60)

    X, y = load_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
    X_train, X_val, X_test, scaler = normalize(X_train, X_val, X_test)
    save_tensors(X_train, X_val, X_test, y_train, y_val, y_test)

    print("\n✓ Preprocessing complete.")


if __name__ == "__main__":
    main()
