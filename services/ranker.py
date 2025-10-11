import math
from collections import defaultdict
from datetime import datetime

def freshness(created_at_str, tau_days=30):
    try:
        dt = datetime.fromisoformat(created_at_str.replace("Z", ""))
        days = (datetime.utcnow() - dt).days
        return math.exp(-days / tau_days)
    except:
        return 1.0

def meta_match(user_pref_tags: set, candidate_tags: list, same_series: bool):
    tag_overlap = len(user_pref_tags.intersection(set(candidate_tags or [])))
    return min(1.0, 0.2*tag_overlap + (0.2 if same_series else 0.0))

def blend(cosine, bm25, meta, fresh):
    return 0.6*cosine + 0.2*bm25 + 0.1*meta + 0.1*fresh

def diversify(items, key="series", max_per=3):
    buckets = defaultdict(int); out=[]
    for it in items:
        k = it["metadata"].get(key)
        if buckets[k] < max_per:
            out.append(it); buckets[k] += 1
    return out