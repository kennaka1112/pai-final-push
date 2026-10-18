#!/usr/bin/env python3
"""学習ログ（step: N loss: X の行）から損失曲線を描く。
   使い方: plot_loss.py 入力ログ 出力PNG"""
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

log_path, out_path = sys.argv[1], sys.argv[2]
steps, losses = [], []
pat = re.compile(r'step:\s*(\d+)\s+loss:\s*([0-9.]+)')
with open(log_path, encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = pat.search(line)
        if m:
            steps.append(int(m.group(1)))
            losses.append(float(m.group(2)))

fig, ax = plt.subplots(figsize=(8, 4.2), dpi=140)
ax.plot(steps, losses, color='#2d6cdf', linewidth=1.8)
ax.set_yscale('log')
ax.set_xlabel('training step')
ax.set_ylabel('loss (log scale)')
ax.set_title(f'ACT training loss  (final: {losses[-1]:.3f} @ step {steps[-1]})')
ax.grid(alpha=0.3, which='both')
fig.tight_layout()
fig.savefig(out_path, facecolor='white')
print(f'saved: {out_path}  points={len(steps)}')
