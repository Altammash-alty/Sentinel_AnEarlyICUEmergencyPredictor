"""
SENTINEL — Synthetic Patient Data Generator
Generates 10,000 patient sequences with realistic vital sign patterns
for three patient states: Stable, Deteriorating, Critical.
"""

import numpy as np
import pandas as pd
import os
import sys

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

RANDOM_SEED = 42
N_SEQUENCES = 10_000
N_STEPS = 60  # 60 time steps per sequence (1 minute each)
N_VITALS = 5  # HR, BP_sys, SpO2, RR, Temp

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)

np.random.seed(RANDOM_SEED)

# ──────────────────────────────────────────────────────────────────────────────
# Patient Baselines
# ──────────────────────────────────────────────────────────────────────────────

PATIENT_TYPES = {
    "healthy_adult": {
        "HR": 72.0, "BP_sys": 120.0, "SpO2": 98.0, "RR": 14.0, "Temp": 36.6,
    },
    "elderly": {
        "HR": 76.0, "BP_sys": 135.0, "SpO2": 95.0, "RR": 18.0, "Temp": 36.8,
    },
    "post_surgery": {
        "HR": 88.0, "BP_sys": 110.0, "SpO2": 96.0, "RR": 20.0, "Temp": 37.2,
    },
    "sepsis_risk": {
        "HR": 95.0, "BP_sys": 105.0, "SpO2": 94.0, "RR": 22.0, "Temp": 38.5,
    },
    "cardiac_risk": {
        "HR": 82.0, "BP_sys": 145.0, "SpO2": 96.0, "RR": 16.0, "Temp": 37.0,
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Physiological valid ranges for clipping
# ──────────────────────────────────────────────────────────────────────────────

VITALS_RANGES = {
    "HR":     (20.0, 220.0),
    "BP_sys": (50.0, 250.0),
    "SpO2":   (70.0, 100.0),
    "RR":     (4.0,  60.0),
    "Temp":   (34.0, 42.0),
}

# ──────────────────────────────────────────────────────────────────────────────
# Noise standard deviations
# ──────────────────────────────────────────────────────────────────────────────

NOISE_STD = {
    "HR":     2.0,
    "BP_sys": 3.0,
    "SpO2":   0.5,
    "RR":     1.0,
    "Temp":   0.1,
}

# Label distribution
LABEL_DIST = {
    0: 0.40,  # STABLE
    1: 0.35,  # DETERIORATING
    2: 0.25,  # CRITICAL
}


# ──────────────────────────────────────────────────────────────────────────────
# Sequence generators
# ──────────────────────────────────────────────────────────────────────────────

def add_noise(sequence: np.ndarray) -> np.ndarray:
    """Add realistic Gaussian noise to a (N_STEPS, N_VITALS) sequence."""
    stds = np.array([
        NOISE_STD["HR"],
        NOISE_STD["BP_sys"],
        NOISE_STD["SpO2"],
        NOISE_STD["RR"],
        NOISE_STD["Temp"],
    ])
    noise = np.random.randn(N_STEPS, N_VITALS) * stds
    return sequence + noise


def clip_sequence(sequence: np.ndarray) -> np.ndarray:
    """Clip vitals to physiologically valid ranges."""
    mins = np.array([20.0, 50.0, 70.0, 4.0, 34.0])
    maxs = np.array([220.0, 250.0, 100.0, 60.0, 42.0])
    return np.clip(sequence, mins, maxs)


def get_baseline_array(baseline: dict) -> np.ndarray:
    """Return baseline as numpy array in column order [HR, BP, SpO2, RR, Temp]."""
    return np.array([
        baseline["HR"],
        baseline["BP_sys"],
        baseline["SpO2"],
        baseline["RR"],
        baseline["Temp"],
    ])


def generate_stable(baseline: dict) -> np.ndarray:
    """
    STABLE sequence: all vitals stay within ±5% of baseline.
    Small Gaussian noise only; no directional trends.
    """
    base = get_baseline_array(baseline)
    # Small random drift within ±5%
    drift_range = base * 0.05
    drift = np.random.uniform(-drift_range, drift_range, size=(N_STEPS, N_VITALS))
    sequence = np.tile(base, (N_STEPS, 1)) + drift
    sequence = add_noise(sequence)
    return clip_sequence(sequence)


def generate_deteriorating(baseline: dict) -> np.ndarray:
    """
    DETERIORATING sequence: gradual drift starting at a random step 20-40.
    """
    base = get_baseline_array(baseline)
    drift_start = np.random.randint(20, 41)

    sequence = np.tile(base, (N_STEPS, 1)).astype(float)

    # Per-step drift rates: [HR, BP, SpO2, RR, Temp]
    rates = np.array([+0.5, -0.8, -0.3, +0.3, +0.05])

    for step in range(drift_start, N_STEPS):
        elapsed = step - drift_start
        sequence[step] = base + rates * elapsed

    sequence = add_noise(sequence)
    return clip_sequence(sequence)


def generate_critical(baseline: dict) -> np.ndarray:
    """
    CRITICAL sequence: sudden acute event at random step 35-55, then continues
    with deteriorating trend after the event.
    """
    base = get_baseline_array(baseline)
    event_step = np.random.randint(35, 56)

    sequence = np.tile(base, (N_STEPS, 1)).astype(float)

    # Event magnitude deltas: [HR, BP, SpO2, RR, Temp]
    hr_jump   = np.random.uniform(40, 60)
    spo2_drop = np.random.uniform(-15, -8)
    bp_drop   = np.random.uniform(-50, -30)
    rr_jump   = np.random.uniform(10, 15)
    temp_spike = np.random.uniform(1.5, 2.5)

    event_delta = np.array([hr_jump, bp_drop, spo2_drop, rr_jump, temp_spike])

    # Gradual drift rates after event
    post_rates = np.array([+0.5, -0.8, -0.3, +0.3, +0.05])

    for step in range(event_step, N_STEPS):
        elapsed = step - event_step
        sequence[step] = base + event_delta + post_rates * elapsed

    sequence = add_noise(sequence)
    return clip_sequence(sequence)


# ──────────────────────────────────────────────────────────────────────────────
# Main generation loop
# ──────────────────────────────────────────────────────────────────────────────

def generate_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate the full dataset and return two DataFrames."""

    patient_type_names = list(PATIENT_TYPES.keys())

    # Pre-compute label counts
    n_stable = int(N_SEQUENCES * LABEL_DIST[0])
    n_det    = int(N_SEQUENCES * LABEL_DIST[1])
    n_crit   = N_SEQUENCES - n_stable - n_det  # remainder goes to critical

    labels_list = [0] * n_stable + [1] * n_det + [2] * n_crit
    np.random.shuffle(labels_list)

    sequences_rows = []
    label_rows = []

    print(f"Generating {N_SEQUENCES} patient sequences ...")
    print(f"  Stable={n_stable}, Deteriorating={n_det}, Critical={n_crit}")

    for seq_id, label in enumerate(labels_list):
        if seq_id % 1000 == 0:
            print(f"  Progress: {seq_id}/{N_SEQUENCES}", end="\r", flush=True)

        # Pick a random patient type
        pt_name = np.random.choice(patient_type_names)
        baseline = PATIENT_TYPES[pt_name]

        # Generate the sequence
        if label == 0:
            seq = generate_stable(baseline)
        elif label == 1:
            seq = generate_deteriorating(baseline)
        else:
            seq = generate_critical(baseline)

        # Flatten into rows
        for step in range(N_STEPS):
            sequences_rows.append({
                "seq_id":  seq_id,
                "step":    step,
                "HR":      round(seq[step, 0], 2),
                "BP_sys":  round(seq[step, 1], 2),
                "SpO2":    round(seq[step, 2], 2),
                "RR":      round(seq[step, 3], 2),
                "Temp":    round(seq[step, 4], 2),
                "label":   label,
            })

        label_rows.append({
            "seq_id":       seq_id,
            "label":        label,
            "patient_type": pt_name,
        })

    print(f"\nAll {N_SEQUENCES} sequences generated.")

    sequences_df = pd.DataFrame(sequences_rows)
    labels_df    = pd.DataFrame(label_rows)
    return sequences_df, labels_df


def main():
    sequences_df, labels_df = generate_dataset()

    seq_path   = os.path.join(OUTPUT_DIR, "patient_sequences.csv")
    label_path = os.path.join(OUTPUT_DIR, "training_labels.csv")

    sequences_df.to_csv(seq_path,   index=False)
    labels_df.to_csv(label_path, index=False)

    print(f"\n✓ Saved sequences  → {seq_path}")
    print(f"✓ Saved labels     → {label_path}")
    print(f"\nDataset summary:")
    print(f"  Total rows in sequences CSV : {len(sequences_df):,}")
    print(f"  Unique sequences             : {sequences_df['seq_id'].nunique():,}")
    print(f"  Steps per sequence           : {N_STEPS}")
    print(f"  Label distribution:\n{labels_df['label'].value_counts().sort_index()}")


if __name__ == "__main__":
    main()
