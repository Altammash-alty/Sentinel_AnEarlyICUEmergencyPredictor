"""
SENTINEL — LSTM Model Architecture (PyTorch)

Architecture:
  Input  : (batch, 60, 5)
  → LSTM1 : hidden_size=128, dropout=0.2
  → LSTM2 : hidden_size=64,  dropout=0.2
  → FC    : 64 → 32  (ReLU)
  → Dropout: 0.3
  → FC    : 32 → 3
  → Softmax → [P(stable), P(deteriorating), P(critical)]
"""

import torch
import torch.nn as nn


class SentinelLSTM(nn.Module):
    """
    Two-layer stacked LSTM followed by a two-layer classifier head.
    Produces a 3-class probability distribution over patient states.
    """

    def __init__(
        self,
        input_size: int = 5,
        hidden1: int = 128,
        hidden2: int = 64,
        fc_hidden: int = 32,
        num_classes: int = 3,
        lstm_dropout: float = 0.2,
        fc_dropout: float = 0.3,
    ):
        super().__init__()

        self.hidden1 = hidden1
        self.hidden2 = hidden2

        # ── LSTM stack ──────────────────────────────────────────────────────
        self.lstm1 = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden1,
            num_layers=1,
            batch_first=True,
            dropout=0.0,        # dropout only between layers, not inside a single layer
        )
        self.lstm1_dropout = nn.Dropout(p=lstm_dropout)

        self.lstm2 = nn.LSTM(
            input_size=hidden1,
            hidden_size=hidden2,
            num_layers=1,
            batch_first=True,
            dropout=0.0,
        )
        self.lstm2_dropout = nn.Dropout(p=lstm_dropout)

        # ── Classifier head ─────────────────────────────────────────────────
        self.fc1    = nn.Linear(hidden2, fc_hidden)
        self.relu   = nn.ReLU()
        self.fc_drop = nn.Dropout(p=fc_dropout)
        self.fc2    = nn.Linear(fc_hidden, num_classes)

        # ── Output ──────────────────────────────────────────────────────────
        self.softmax = nn.Softmax(dim=-1)

        # Weight initialization
        self._init_weights()

    def _init_weights(self):
        """Xavier uniform init for linear layers; orthogonal for LSTM recurrent weights."""
        for name, param in self.lstm1.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param)
            elif "bias" in name:
                nn.init.zeros_(param)

        for name, param in self.lstm2.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param)
            elif "bias" in name:
                nn.init.zeros_(param)

        nn.init.xavier_uniform_(self.fc1.weight)
        nn.init.zeros_(self.fc1.bias)
        nn.init.xavier_uniform_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x : (batch_size, seq_len, input_size)  — already normalized vitals

        Returns:
            probs : (batch_size, 3)  — [P(stable), P(det), P(critical)]
        """
        # ── LSTM 1 ──────────────────────────────────────────────────────────
        out1, _ = self.lstm1(x)                   # (B, T, 128)
        out1    = self.lstm1_dropout(out1)

        # ── LSTM 2 ──────────────────────────────────────────────────────────
        out2, _ = self.lstm2(out1)                # (B, T, 64)
        out2    = self.lstm2_dropout(out2)

        # Take only the last time step
        last_hidden = out2[:, -1, :]              # (B, 64)

        # ── Classifier ──────────────────────────────────────────────────────
        x = self.fc1(last_hidden)                 # (B, 32)
        x = self.relu(x)
        x = self.fc_drop(x)
        x = self.fc2(x)                           # (B, 3)
        probs = self.softmax(x)                   # (B, 3)

        return probs

    # ── Convenience helpers ─────────────────────────────────────────────────

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Inference-time wrapper (no gradient computation)."""
        self.eval()
        with torch.no_grad():
            return self.forward(x)

    def predict_class(self, x: torch.Tensor) -> torch.Tensor:
        """Return the argmax class label."""
        probs = self.predict_proba(x)
        return torch.argmax(probs, dim=-1)

    def extra_repr(self) -> str:
        return (
            f"lstm1_hidden={self.hidden1}, lstm2_hidden={self.hidden2}, "
            f"output_classes=3"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Quick model summary when run directly
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    model = SentinelLSTM()
    print(model)
    print()

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable    = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters    : {total_params:,}")
    print(f"Trainable parameters: {trainable:,}")

    # Test forward pass
    batch = torch.randn(16, 60, 5)
    probs = model(batch)
    print(f"\nForward pass — input shape : {batch.shape}")
    print(f"Forward pass — output shape: {probs.shape}")
    print(f"Sample probabilities (first item): {probs[0].detach().numpy()}")
    assert probs.shape == (16, 3), "Output shape mismatch!"
    assert abs(probs[0].sum().item() - 1.0) < 1e-5, "Probabilities do not sum to 1!"
    print("\n✓ Model architecture verified.")
