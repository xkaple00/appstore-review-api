from collections import Counter
from sqlalchemy.orm import Session
from ..models import Review

def compute_metrics(db: Session, app_id: str, country: str):
    rows = db.query(Review).filter_by(app_id=app_id, country=country).all()
    if not rows:
        return {"count":0, "average_rating":0.0, "distribution":{}}
    ratings = [r.rating for r in rows if r.rating is not None]
    avg = sum(ratings)/len(ratings) if ratings else 0.0
    c = Counter(ratings)
    total = len(ratings)
    dist = {str(k): round(v*100.0/total,2) for k,v in sorted(c.items())}
    return {"count": total, "average_rating": round(avg,2), "distribution": dist}
