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

## 2. Baseline Benchmark Results (Phase 4 & Phase 5)

Recorded from `scripts/evaluate_retrieval.py` (`data/evaluation_baseline.json`):

### Comparative Search Mode Evaluation

| Metric | `frame_semantic_v1` | `video_window_v1` | `hybrid_v1` | Notes |
|---|---|---|---|---|
| **Recall@1** | **1.0** (100%) | **1.0** (100%) | **1.0** (100%) | All modes successfully rank matching intervals at #1 |
| **Recall@3** | **1.0** (100%) | **1.0** (100%) | **1.0** (100%) | Consistent coverage |
| **Recall@5** | **1.0** (100%) | **1.0** (100%) | **1.0** (100%) | Consistent coverage |
| **Mean tIoU** | **0.60** (60%) | **0.35** (35%) | **0.60** (60%) | Frame search provides tighter boundaries for discrete events |
| **Mean Search Latency** | **6.17 ms** | **8.99 ms** | **12.53 ms** | Sub-15ms across all retrieval strategies |
| **Indexing Throughput** | **0.37s / 5s media** | **0.37s / 5s media** | **0.37s / 5s media** | Extracting frames + windows in single pipeline pass |

> [!NOTE]
> **Key Finding:** Frame-only retrieval provides tighter temporal IoU for sudden/discrete events on this benchmark, while video-window retrieval pools activity over fixed 4.0s spans. Hybrid mode maintains high tIoU while expanding candidate temporal evidence. Neither mode is universally superior across all queries; selection depends on action duration.

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
