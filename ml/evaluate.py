"""
SENTINEL — Model Evaluation Script

Loads the trained model + test set and prints:
  - Overall accuracy
  - Per-class precision, recall, F1
  - Confusion matrix
  - ROC-AUC per class (one-vs-rest)
"""

import os
import sys
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lstm_model import SentinelLSTM

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

ML_DIR     = os.path.dirname(os.path.abspath(__file__))
PROCESSED  = os.path.join(ML_DIR, "processed")
MODEL_PATH = os.path.join(ML_DIR, "saved_model", "sentinel_lstm.pt")

DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CLASS_NAMES = ["Stable", "Deteriorating", "Critical"]


# ──────────────────────────────────────────────────────────────────────────────
# Load model
# ──────────────────────────────────────────────────────────────────────────────

def load_model() -> SentinelLSTM:
    model = SentinelLSTM()
    checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    model.to(DEVICE)
    model.eval()
    print(f"✓ Loaded model from epoch {checkpoint['epoch']}  "
          f"(val_loss={checkpoint['val_loss']:.4f})")
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Load test set
# ──────────────────────────────────────────────────────────────────────────────

def load_test_data():
    X_test = np.load(os.path.join(PROCESSED, "X_test.npy"))
    y_test = np.load(os.path.join(PROCESSED, "y_test.npy"))
    print(f"✓ Test set loaded: X={X_test.shape}  y={y_test.shape}")
    return X_test, y_test


# ──────────────────────────────────────────────────────────────────────────────
# Run inference in batches
# ──────────────────────────────────────────────────────────────────────────────

def get_predictions(model: SentinelLSTM, X: np.ndarray, batch_size: int = 256):
    """Return (y_pred classes, y_proba softmax) for the full test set."""
    X_tensor = torch.FloatTensor(X)
    all_probs = []

    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i : i + batch_size].to(DEVICE)
            probs = model(batch)
            all_probs.append(probs.cpu().numpy())

    all_probs = np.vstack(all_probs)          # (N, 3)
    y_pred    = np.argmax(all_probs, axis=1)  # (N,)
    return y_pred, all_probs


# ──────────────────────────────────────────────────────────────────────────────
# Print utilities
# ──────────────────────────────────────────────────────────────────────────────

def print_confusion_matrix(cm: np.ndarray):
    print("\nConfusion Matrix:")
    header = "             " + "  ".join(f"{n:>13}" for n in CLASS_NAMES)
    print(header)
    print(" " * 13 + "─" * (len(CLASS_NAMES) * 15))
    for i, row in enumerate(cm):
        row_str = "  ".join(f"{v:>13,}" for v in row)
        print(f"  {CLASS_NAMES[i]:>11}  {row_str}")


def print_roc_auc(y_true: np.ndarray, y_proba: np.ndarray):
    print("\nROC-AUC (one-vs-rest):")
    from sklearn.preprocessing import label_binarize
    y_bin = label_binarize(y_true, classes=[0, 1, 2])

    for i, name in enumerate(CLASS_NAMES):
        auc = roc_auc_score(y_bin[:, i], y_proba[:, i])
        print(f"  {name:>14} : {auc:.4f}")

    macro_auc = roc_auc_score(y_bin, y_proba, average="macro", multi_class="ovr")
    print(f"  {'Macro-avg':>14} : {macro_auc:.4f}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def evaluate():
    print("=" * 60)
    print("SENTINEL — Model Evaluation")
    print("=" * 60)

    model        = load_model()
    X_test, y_test = load_test_data()
    y_pred, y_proba = get_predictions(model, X_test)

    # ── Overall accuracy ─────────────────────────────────────────────
    acc = accuracy_score(y_test, y_pred)
    print(f"\nOverall Accuracy: {acc*100:.2f}%")

    # ── Per-class report ─────────────────────────────────────────────
    print("\nClassification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=CLASS_NAMES,
        digits=4
    ))

    # ── Confusion matrix ─────────────────────────────────────────────
    cm = confusion_matrix(y_test, y_pred)
    print_confusion_matrix(cm)

    # ── ROC-AUC ──────────────────────────────────────────────────────
    print_roc_auc(y_test, y_proba)

    print("\n✓ Evaluation complete.")


if __name__ == "__main__":
    evaluate()
