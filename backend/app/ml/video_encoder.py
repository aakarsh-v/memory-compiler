import math
from typing import List
from app.db.models import Frame


class VideoWindowEncoder:
    """
    Temporal video-window embedding aggregator.
    Pools and normalizes visual frame representations across sliding time windows.
    """

    def __init__(self, dimension: int = 512, model_id: str = "temporal-window-meanpool-v1"):
        self.dimension = dimension
        self.model_id = model_id

    def encode_window(self, window_frames: List[Frame]) -> List[float]:
        """
        Computes L2-normalized mean-pooled temporal representation over window frames.
        """
        valid_vectors = [f.embedding for f in window_frames if f.embedding and len(f.embedding) == self.dimension]
        if not valid_vectors:
            # Fallback zero/unit vector
            vec = [0.0] * self.dimension
            vec[0] = 1.0
            return vec

        # Mean pooling across time dimension
        pooled = [0.0] * self.dimension
        for vec in valid_vectors:
            for i in range(self.dimension):
                pooled[i] += vec[i]

        count = float(len(valid_vectors))
        pooled = [x / count for x in pooled]

        # L2 normalize
        norm = math.sqrt(sum(x * x for x in pooled))
        if norm == 0.0:
            norm = 1.0
        return [x / norm for x in pooled]

