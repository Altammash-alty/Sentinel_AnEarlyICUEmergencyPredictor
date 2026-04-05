"""
SENTINEL — LSTM Training Script

- Loads preprocessed tensors from ml/processed/
- Trains SentinelLSTM for 50 epochs
- Uses CrossEntropyLoss with class weights (critical x3, deteriorating x2)
- Saves best checkpoint by validation loss
- Prints per-epoch loss + accuracy table
"""

import os
import sys
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau

# Add parent directory so we can import lstm_model
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lstm_model import SentinelLSTM

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

ML_DIR       = os.path.dirname(os.path.abspath(__file__))
PROCESSED    = os.path.join(ML_DIR, "processed")
SAVED_DIR    = os.path.join(ML_DIR, "saved_model")
MODEL_PATH   = os.path.join(SAVED_DIR, "sentinel_lstm.pt")

os.makedirs(SAVED_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Hyperparameters
# ──────────────────────────────────────────────────────────────────────────────

EPOCHS     = 50
BATCH_SIZE = 64
LR         = 1e-3
SEED       = 42

torch.manual_seed(SEED)
np.random.seed(SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training device: {DEVICE}")


# ──────────────────────────────────────────────────────────────────────────────
# Load preprocessed tensors
# ──────────────────────────────────────────────────────────────────────────────

def load_tensors():
    print("\nLoading preprocessed tensors ...")

    X_train = np.load(os.path.join(PROCESSED, "X_train.npy"))
    X_val   = np.load(os.path.join(PROCESSED, "X_val.npy"))
    y_train = np.load(os.path.join(PROCESSED, "y_train.npy"))
    y_val   = np.load(os.path.join(PROCESSED, "y_val.npy"))

    print(f"  X_train: {X_train.shape}  y_train: {y_train.shape}")
    print(f"  X_val:   {X_val.shape}    y_val:   {y_val.shape}")

    # Convert to PyTorch tensors
    Xt = torch.FloatTensor(X_train)
    Xv = torch.FloatTensor(X_val)
    yt = torch.LongTensor(y_train)
    yv = torch.LongTensor(y_val)

    train_ds = TensorDataset(Xt, yt)
    val_ds   = TensorDataset(Xv, yv)

    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                          num_workers=0, pin_memory=(DEVICE.type == "cuda"))
    val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                          num_workers=0, pin_memory=(DEVICE.type == "cuda"))

    return train_dl, val_dl


# ──────────────────────────────────────────────────────────────────────────────
# Class weights  (stable=1.0, deteriorating=2.0, critical=3.0)
# ──────────────────────────────────────────────────────────────────────────────

def compute_class_weights() -> torch.Tensor:
    weights = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
    return weights.to(DEVICE)


# ──────────────────────────────────────────────────────────────────────────────
# Accuracy helper
# ──────────────────────────────────────────────────────────────────────────────

def accuracy(logits_or_probs: torch.Tensor, labels: torch.Tensor) -> float:
    preds = torch.argmax(logits_or_probs, dim=1)
    return (preds == labels).float().mean().item()


# ──────────────────────────────────────────────────────────────────────────────
# One epoch
# ──────────────────────────────────────────────────────────────────────────────

def run_epoch(model, loader, criterion, optimizer=None, train=True):
    if train:
        model.train()
    else:
        model.eval()

    total_loss, total_acc, n_batches = 0.0, 0.0, 0

    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)

            probs = model(X_batch)
            loss  = criterion(probs, y_batch)

            if train:
                optimizer.zero_grad()
                loss.backward()
                # Gradient clipping for stability
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

            total_loss += loss.item()
            total_acc  += accuracy(probs, y_batch)
            n_batches  += 1

    return total_loss / n_batches, total_acc / n_batches


# ──────────────────────────────────────────────────────────────────────────────
# Training loop
# ──────────────────────────────────────────────────────────────────────────────

def train():
    train_dl, val_dl = load_tensors()

    model     = SentinelLSTM().to(DEVICE)
    weights   = compute_class_weights()
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = Adam(model.parameters(), lr=LR)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", patience=5, factor=0.5)

    best_val_loss = float("inf")
    best_epoch    = -1

    header = f"{'Epoch':>6}  {'Train Loss':>10}  {'Train Acc':>9}  {'Val Loss':>8}  {'Val Acc':>7}  {'LR':>8}  {'Time':>6}"
    divider = "─" * len(header)
    print(f"\n{header}")
    print(divider)

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()

        train_loss, train_acc = run_epoch(model, train_dl, criterion, optimizer, train=True)
        val_loss,   val_acc   = run_epoch(model, val_dl,   criterion,            train=False)

        scheduler.step(val_loss)
        elapsed = time.time() - t0
        current_lr = optimizer.param_groups[0]["lr"]

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch    = epoch
            torch.save({
                "epoch":          epoch,
                "model_state":    model.state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "val_loss":       val_loss,
                "val_acc":        val_acc,
            }, MODEL_PATH)
            marker = " ← best"
        else:
            marker = ""

        print(
            f"{epoch:>6}  {train_loss:>10.4f}  {train_acc:>9.4f}  "
            f"{val_loss:>8.4f}  {val_acc:>7.4f}  {current_lr:>8.6f}  "
            f"{elapsed:>5.1f}s{marker}"
        )

    print(divider)
    print(f"\n✓ Training complete.")
    print(f"  Best epoch     : {best_epoch}")
    print(f"  Best val loss  : {best_val_loss:.4f}")
    print(f"  Model saved    : {MODEL_PATH}")
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("SENTINEL — LSTM Training")
    print("=" * 60)
    train()
