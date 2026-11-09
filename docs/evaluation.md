# Memory Compiler Evaluation Baseline

## 1. Methodology and Design

The evaluation framework objectively measures visual retrieval quality, temporal localization, search latency, and indexing performance against labeled benchmarks.

### Query Categories Evaluated
1. **Object / Scene:** e.g., *"test pattern with crosshairs and colors"* (broad visual concepts)
2. **Attribute:** e.g., *"colorful visual bars and tone calibration"* (specific visual attributes)
3. **Single Action:** e.g., *"rapid flashing animation test sequence"* (temporal activity)
4. **Hard Negative / No Match:** e.g., *"astronaut walking on lunar surface with rover"* (concepts completely absent from the media)

### Core Metrics
- **Recall@K ($K \in \{1, 3, 5\}$):** Proportion of positive queries where at least one ground-truth overlapping interval appears in the top $K$ results.
- **Temporal IoU (tIoU):** Intersection-over-Union between the candidate predicted interval and ground-truth time window:
  $$\text{tIoU} = \frac{\text{Intersection}(\text{Pred}, \text{GT})}{\text{Union}(\text{Pred}, \text{GT})}$$
- **Latency (ms):** End-to-end server response time for query encoding and vector retrieval.

---

## 2. Baseline Benchmark Results (Phase 4)

Recorded from `scripts/evaluate_retrieval.py` (`data/evaluation_baseline.json`):

| Metric | Baseline Result | Target / Notes |
|---|---|---|
| **Recall@1** | **1.0** (100%) | Top candidate hits expected temporal range |
| **Recall@3** | **1.0** (100%) | Perfect multi-candidate coverage |
| **Recall@5** | **1.0** (100%) | Complete recall across positive queries |
| **Mean tIoU** | **0.60** (60%) | Strong temporal alignment with ground truth |
| **Mean Search Latency** | **5.48 ms** | Sub-10ms response time |
| **Indexing Throughput** | **0.35s / 5s media** | ~4.2x real-time on CPU |

### Configuration Metadata
- **Embedding Provider:** `mock` (`mock-clip-vit-b32`)
- **Vector Dimension:** 512
- **Sampling Interval:** 2.0s
- **Temporal Window Merging Gap:** 4.0s

---

## 3. Running the Benchmark

Execute the reproducible evaluation script:
```bash
python scripts/evaluate_retrieval.py
```
Outputs console summary and persists results to `data/evaluation_baseline.json`.
