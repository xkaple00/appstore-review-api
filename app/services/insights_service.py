from typing import List
from collections import Counter
from sqlalchemy.orm import Session
from ..models import Review
from ..nlp.sentiment import classify_sentiment
from ..nlp.keywords import top_keywords
from ..nlp.recommender_llm import generate_recommendations_from_reviews


def analyze_insights(db: Session, app_id: str, country: str):
    rows = db.query(Review).filter_by(app_id=app_id, country=country).all()
    sentiments = [classify_sentiment(r.text) for r in rows]
    c = Counter(sentiments)
    total = len(sentiments) if sentiments else 1
    percent = {k: round(v*100.0/total,2) for k,v in c.items()}

    negatives = [r.text for r in rows if classify_sentiment(r.text) == 'negative']
    neg_keywords = top_keywords(negatives, top_k=15)

    recs = generate_recommendations_from_reviews(negatives)

    return {
        "sentiment_counts": dict(c),
        "sentiment_percent": percent,
        "top_negative_keywords": neg_keywords,
        "recommendations": recs
    }
