import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import Video, Frame
from app.ml.factory import get_embedding_provider
import math

def cos_sim(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2)

db = SessionLocal()
provider = get_embedding_provider()

for q in ['hair', 'game', 'playing game', 'person']:
    print(f"\n==========================================")
    print(f"QUERY: '{q}'")
    print(f"==========================================")
    
    # 1. Bare
    bare_vec = provider.embed_texts([q])[0]
    
    # 2. Templated
    templated_vec = provider.embed_texts([f"a video frame of {q}"])[0]

    # 3. Ensemble
    templates = [f"a video of {q}", f"a photo of {q}", f"a scene showing {q}", f"{q}"]
    t_vecs = provider.embed_texts(templates)
    dim = len(t_vecs[0])
    ensemble_vec = [sum(v[i] for v in t_vecs) / len(t_vecs) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in ensemble_vec))
    ensemble_vec = [x / norm for x in ensemble_vec]

    videos = db.query(Video).filter(Video.status == 'READY').all()
    for mode_name, vec in [('Bare', bare_vec), ('Templated ("a video frame of...")', templated_vec), ('Ensemble (4 templates)', ensemble_vec)]:
        scores = []
        for v in videos:
            frames = db.query(Frame).filter(Frame.video_id == v.id).all()
            for f in frames:
                scores.append((cos_sim(vec, f.embedding), v.filename, f.timestamp_seconds))
        scores.sort(key=lambda x: x[0], reverse=True)
        print(f"  [{mode_name} Top 3]:")
        for s, name, ts in scores[:3]:
            print(f"    {s:.4f} | {name} @ {ts}s")

db.close()
