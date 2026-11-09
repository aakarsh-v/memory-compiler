import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db.models import Video, Frame
from app.ml.factory import get_embedding_provider
import math

def cos_sim(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    return dot / (math.sqrt(sum(a*a for a in v1)) * math.sqrt(sum(b*b for b in v2)))

db = SessionLocal()
provider = get_embedding_provider()

test_queries = [
    'Pikachu Pokemon in grid',
    'anime characters with flute',
    'SMPTE television color bars',
    'tic tac toe board',
    'Lord Krishna playing flute with Radha',
    'green forest background with yellow creatures'
]

videos = db.query(Video).filter(Video.status == 'READY').all()

for q in test_queries:
    print(f"\n=== QUERY: '{q}' ===")
    q_vec = provider.embed_texts([q])[0]
    rank = []
    for v in videos:
        frames = db.query(Frame).filter(Frame.video_id == v.id).all()
        best = max(cos_sim(q_vec, f.embedding) for f in frames) if frames else 0
        rank.append((best, v.filename))
    rank.sort(reverse=True)
    for s, name in rank:
        print(f"  {s:.4f} | {name}")

db.close()

