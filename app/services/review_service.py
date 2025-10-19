import os, random, datetime as dt
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from ..models import Review
from ..utils.text import clean_text
from ..collectors.rss_client import RSSCollector

def upsert_reviews(db: Session, app_id: str, country: str, rows: List[Dict]) -> int:
    inserted = 0
    for r in rows:
        if not r.get('rating'):
            continue
        rv = db.query(Review).filter_by(app_id=app_id, country=country, review_id=r['review_id']).first()
        if rv:
            continue
        rv = Review(
            app_id=app_id,
            country=country,
            review_id=r.get('review_id') or f"rss-{random.getrandbits(32)}",
            author=clean_text(r.get('author',"")),
            title=clean_text(r.get('title',"")),
            text=clean_text(r.get('text',"")),
            rating=int(r.get('rating',0)),
            version=str(r.get('version',"")),
            date=r.get('date'),
            source=r.get('source',''),
            language=r.get('language','')
        )
        db.add(rv)
        inserted += 1
    db.commit()
    return inserted

def collect_reviews(db: Session, app_id: str, country: str, how_many: int, source: str = "auto") -> Tuple[int, int]:
    pool: List[Dict] = []
    errors = []
    src_order = ["webscraper","rss"] if source in ("auto","webscraper") else ([source] if source!="auto" else ["rss"])

    for src in src_order:
        try:
            pool = RSSCollector().fetch(app_id, country, max_pages=10)
        except Exception as e:
            errors.append(str(e))
            continue

    if not pool:
        return (0, 0)

    random.shuffle(pool)
    sample = pool[:how_many]
    before = db.query(Review).filter_by(app_id=app_id, country=country).count()
    inserted = upsert_reviews(db, app_id, country, sample)
    after = db.query(Review).filter_by(app_id=app_id, country=country).count()
    return (inserted, after - before)
