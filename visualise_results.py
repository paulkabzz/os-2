#!/usr/bin/env python3
"""
visualise_results.py — Analyse and graph scheduling simulation results.

Reads all CSVs from results/, produces publication-quality figures comparing
FCFS, SJF, Priority, and MLFQ across the key metrics from the assignment spec:
  1. Average waiting time (per order)
  2. Average response time (per order)
  3. Average turnaround time (per order)
  4. Total waiting time per patron
  5. Throughput (orders / second)
  6. Distributions (box plots) for fairness & predictability
  7. Per-patron total waiting time (starvation detection)

All figures are saved to results/figures/.
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── Configuration ──────────────────────────────────────────────────────────
RESULTS_DIR = "results"
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
SCHEDULERS = ["FCFS", "SJF", "PRIORITY", "MLFQ"]
COLORS = {
    "FCFS":     "#4C72B0",
    "SJF":      "#55A868",
    "PRIORITY": "#C44E52",
    "MLFQ":     "#8172B2",
}
os.makedirs(FIGURES_DIR, exist_ok=True)

# ── Styling ────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "#F8F8F8",
    "axes.edgecolor":    "#CCCCCC",
    "axes.grid":         True,
    "grid.alpha":        0.4,
    "grid.linestyle":    "--",
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.labelsize":    12,
    "legend.fontsize":   10,
    "figure.dpi":        150,
    "savefig.dpi":       150,
    "savefig.bbox":      "tight",
})


# ── Load data ──────────────────────────────────────────────────────────────
def load_all_csvs(results_dir):
    """Load every CSV in results_dir into a single DataFrame."""
    files = glob.glob(os.path.join(results_dir, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {results_dir}/")

    frames = []
    for f in sorted(files):
        basename = os.path.basename(f)
        parts = basename.replace(".csv", "").split("_")
        # e.g. FCFS_10_1.csv → scheduler=FCFS, nPatrons=10, seed=1
        sched = parts[0]
        n_patrons = int(parts[1])
        seed = int(parts[2])

        df = pd.read_csv(f)
        df["nPatrons"] = n_patrons
        df["seed"] = seed
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


df = load_all_csvs(RESULTS_DIR)
patron_counts = sorted(df["nPatrons"].unique())
print(f"Loaded {len(df)} order records across {df['seed'].nunique()} seeds "
      f"and patron counts {patron_counts}")


# ── Helper: grouped bar chart ─────────────────────────────────────────────
def grouped_bar(ax, data_dict, patron_counts, ylabel, title):
    """Draw a grouped bar chart: one group per patron count, one bar per scheduler."""
    x = np.arange(len(patron_counts))
    n = len(SCHEDULERS)
    width = 0.8 / n

    for i, sched in enumerate(SCHEDULERS):
        vals = [data_dict[(sched, pc)] for pc in patron_counts]
        bars = ax.bar(x + i * width - 0.4 + width / 2, vals, width,
                      label=sched, color=COLORS[sched], edgecolor="white", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([str(pc) for pc in patron_counts])
    ax.set_xlabel("Number of Patrons")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 1 — Average Waiting, Response, and Turnaround Time (per order)
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for col_idx, (metric, label) in enumerate([
    ("waitingTime",    "Avg Waiting Time (ms)"),
    ("responseTime",   "Avg Response Time (ms)"),
    ("turnaroundTime", "Avg Turnaround Time (ms)"),
]):
    # Average across all seeds for each (scheduler, nPatrons)
    agg = df.groupby(["scheduler", "nPatrons"])[metric].mean()
    data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
    grouped_bar(axes[col_idx], data, patron_counts, label,
                f"Average {metric.replace('Time', ' Time')} per Order")

fig.suptitle("Per-Order Timing Metrics by Scheduler", fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "01_avg_times_per_order.png"))
print("Saved 01_avg_times_per_order.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 2 — Median Waiting, Response, and Turnaround Time (per order)
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for col_idx, (metric, label) in enumerate([
    ("waitingTime",    "Median Waiting Time (ms)"),
    ("responseTime",   "Median Response Time (ms)"),
    ("turnaroundTime", "Median Turnaround Time (ms)"),
]):
    agg = df.groupby(["scheduler", "nPatrons"])[metric].median()
    data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
    grouped_bar(axes[col_idx], data, patron_counts, label,
                f"Median {metric.replace('Time', ' Time')} per Order")

fig.suptitle("Median Per-Order Timing Metrics by Scheduler", fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "02_median_times_per_order.png"))
print("Saved 02_median_times_per_order.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 3 — Distributions (Box Plots) of Waiting Time
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, len(patron_counts), figsize=(5 * len(patron_counts), 5),
                         sharey=True)
if len(patron_counts) == 1:
    axes = [axes]

for ax, pc in zip(axes, patron_counts):
    data_to_plot = []
    labels = []
    for sched in SCHEDULERS:
        subset = df[(df["scheduler"] == sched) & (df["nPatrons"] == pc)]["waitingTime"]
        data_to_plot.append(subset.values)
        labels.append(sched)

    bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True, showfliers=True,
                    flierprops=dict(marker="o", markersize=3, alpha=0.4))
    for patch, sched in zip(bp["boxes"], SCHEDULERS):
        patch.set_facecolor(COLORS[sched])
        patch.set_alpha(0.7)

    ax.set_title(f"{pc} Patrons")
    ax.set_ylabel("Waiting Time (ms)" if ax == axes[0] else "")

fig.suptitle("Distribution of Waiting Times (Predictability & Fairness)",
             fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "03_waiting_time_boxplots.png"))
print("Saved 03_waiting_time_boxplots.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 4 — Distributions (Box Plots) of Turnaround Time
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, len(patron_counts), figsize=(5 * len(patron_counts), 5),
                         sharey=True)
if len(patron_counts) == 1:
    axes = [axes]

for ax, pc in zip(axes, patron_counts):
    data_to_plot = []
    labels = []
    for sched in SCHEDULERS:
        subset = df[(df["scheduler"] == sched) & (df["nPatrons"] == pc)]["turnaroundTime"]
        data_to_plot.append(subset.values)
        labels.append(sched)

    bp = ax.boxplot(data_to_plot, tick_labels=labels, patch_artist=True, showfliers=True,
                    flierprops=dict(marker="o", markersize=3, alpha=0.4))
    for patch, sched in zip(bp["boxes"], SCHEDULERS):
        patch.set_facecolor(COLORS[sched])
        patch.set_alpha(0.7)

    ax.set_title(f"{pc} Patrons")
    ax.set_ylabel("Turnaround Time (ms)" if ax == axes[0] else "")

fig.suptitle("Distribution of Turnaround Times",
             fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "04_turnaround_time_boxplots.png"))
print("Saved 04_turnaround_time_boxplots.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 5 — Total Waiting Time per Patron (aggregated)
# ═══════════════════════════════════════════════════════════════════════════
patron_totals = (
    df.groupby(["scheduler", "nPatrons", "seed", "patronID"])["waitingTime"]
    .sum()
    .reset_index()
    .rename(columns={"waitingTime": "totalWaitingTime"})
)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

for col_idx, (func, func_name) in enumerate([
    ("mean",   "Average"),
    ("median", "Median"),
    ("max",    "Maximum"),
]):
    agg = (
        patron_totals.groupby(["scheduler", "nPatrons"])["totalWaitingTime"]
        .agg(func)
    )
    data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
    grouped_bar(axes[col_idx], data, patron_counts,
                f"{func_name} Total Wait (ms)",
                f"{func_name} Total Waiting Time per Patron")

fig.suptitle("Total Waiting Time per Patron (Starvation Indicator)",
             fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "05_total_wait_per_patron.png"))
print("Saved 05_total_wait_per_patron.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 6 — Throughput (orders completed per second)
# ═══════════════════════════════════════════════════════════════════════════
# Throughput = total orders / (last completion − first arrival) per run
throughput_data = []
for (sched, nP, seed), group in df.groupby(["scheduler", "nPatrons", "seed"]):
    duration_ms = group["completionTime"].max() - group["arrivalTime"].min()
    if duration_ms > 0:
        throughput = len(group) / (duration_ms / 1000.0)  # orders per second
    else:
        throughput = 0
    throughput_data.append({
        "scheduler": sched, "nPatrons": nP, "seed": seed,
        "throughput": throughput
    })

tp_df = pd.DataFrame(throughput_data)

fig, ax = plt.subplots(figsize=(8, 5))
agg = tp_df.groupby(["scheduler", "nPatrons"])["throughput"].mean()
data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
grouped_bar(ax, data, patron_counts, "Throughput (orders/sec)",
            "Average Throughput by Scheduler")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "06_throughput.png"))
print("Saved 06_throughput.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 7 — Predictability (Std Dev of Waiting Time)
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 5))
agg = df.groupby(["scheduler", "nPatrons"])["waitingTime"].std()
data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
grouped_bar(ax, data, patron_counts, "Std Dev of Waiting Time (ms)",
            "Predictability: Waiting Time Variability")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "07_predictability.png"))
print("Saved 07_predictability.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 8 — Fairness: Per-Patron Waiting Time (50 patrons, single seed)
# ═══════════════════════════════════════════════════════════════════════════
# Use the largest patron count with seed=1 for a detailed fairness view
fairness_pc = max(patron_counts)
fairness_seed = df[df["nPatrons"] == fairness_pc]["seed"].min()

fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharey=True)
axes = axes.flatten()

for ax, sched in zip(axes, SCHEDULERS):
    subset = df[(df["scheduler"] == sched) &
                (df["nPatrons"] == fairness_pc) &
                (df["seed"] == fairness_seed)]
    patron_waits = subset.groupby("patronID")["waitingTime"].sum()
    ax.bar(patron_waits.index, patron_waits.values,
           color=COLORS[sched], edgecolor="white", linewidth=0.5, alpha=0.85)
    ax.set_title(f"{sched} — {fairness_pc} Patrons (seed {fairness_seed})")
    ax.set_xlabel("Patron ID")
    ax.set_ylabel("Total Waiting Time (ms)")

fig.suptitle("Fairness: Total Waiting Time per Patron",
             fontsize=16, fontweight="bold", y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "08_fairness_per_patron.png"))
print("Saved 08_fairness_per_patron.png")


# ═══════════════════════════════════════════════════════════════════════════
# FIGURE 9 — Starvation: Max Waiting Time for a Single Order
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(8, 5))
agg = df.groupby(["scheduler", "nPatrons"])["waitingTime"].max()
data = {(s, n): agg.get((s, n), 0) for s in SCHEDULERS for n in patron_counts}
grouped_bar(ax, data, patron_counts, "Max Waiting Time (ms)",
            "Worst-Case Waiting Time (Starvation Risk)")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "09_starvation_max_wait.png"))
print("Saved 09_starvation_max_wait.png")

