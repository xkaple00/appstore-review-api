from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from .database import Base, engine, SessionLocal
from .models import Review
from .schemas import CollectRequest, ReviewOut, MetricsOut, InsightsOut
from .services.review_service import collect_reviews
from .services.metrics_service import compute_metrics
from .services.insights_service import analyze_insights
import io, csv, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os, tempfile

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Apple Store Review Analysis API", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/collect")
def collect(req: CollectRequest, db: Session = Depends(get_db)):
    inserted, delta = collect_reviews(db, req.app_id, req.country, req.how_many, req.source)
    return {"status":"ok","inserted": inserted, "new_records": delta}

@app.get("/reviews", response_model=List[ReviewOut])
def list_reviews(app_id: str, country: str, limit: int = Query(default=100, le=1000), db: Session = Depends(get_db)):
    rows = db.query(Review).filter_by(app_id=app_id, country=country).order_by(Review.date.desc().nullslast()).limit(limit).all()
    return [ReviewOut(
        app_id=r.app_id, country=r.country, review_id=r.review_id, author=r.author, title=r.title,
        text=r.text, rating=r.rating, version=r.version, date=r.date, source=r.source, language=r.language
    ) for r in rows]

@app.get("/metrics", response_model=MetricsOut)
def metrics(app_id: str, country: str, db: Session = Depends(get_db)):
    m = compute_metrics(db, app_id, country)
    return {
        "app_id": app_id,
        "country": country,
        **m
    }

@app.get("/insights", response_model=InsightsOut)
def insights(app_id: str, country: str, db: Session = Depends(get_db)):
    data = analyze_insights(db, app_id, country)
    return {
        "app_id": app_id,
        "country": country,
        **data
    }

@app.get("/reviews/download")
def download_reviews(app_id: str, country: str, format: str = "csv", save_local: bool = False, db: Session = Depends(get_db)):
    rows = db.query(Review).filter_by(app_id=app_id, country=country).all()
    if format == "json":
        import json, io
        json_bytes = json.dumps([{
            "app_id": r.app_id, "country": r.country, "review_id": r.review_id, "author": r.author,
            "title": r.title, "text": r.text, "rating": r.rating, "version": r.version,
            "date": (r.date.isoformat() if r.date else None),
            "source": r.source, "language": r.language
        }], ensure_ascii=False, indent=2).encode("utf-8")

        if save_local:
            tmp = tempfile.NamedTemporaryFile("wb", delete=False)
            try:
                tmp.write(json_bytes)
            finally:
                tmp.close()
            os.replace(tmp.name, f"reviews_{app_id}_{country}.json")

        buf = io.BytesIO(json_bytes)
        return StreamingResponse(buf, media_type="application/json",
                                 headers={"Content-Disposition": f'attachment; filename=reviews_{app_id}_{country}.json'})

    # CSV branch
    import io, csv
    s_buf = io.StringIO()
    w = csv.writer(s_buf)
    w.writerow(["app_id","country","review_id","author","title","text","rating","version","date","source","language"])
    for r in rows:
        w.writerow([r.app_id, r.country, r.review_id, r.author, r.title, r.text, r.rating, r.version, r.date, r.source, r.language])

    csv_str = s_buf.getvalue()

    if save_local:
        tmp = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", newline="")
        try:
            tmp.write(csv_str)
        finally:
            tmp.close()
        os.replace(tmp.name, f"reviews_{app_id}_{country}.csv")

    return StreamingResponse(io.BytesIO(csv_str.encode("utf-8")), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename=reviews_{app_id}_{country}.csv'})


@app.get("/report", response_class=HTMLResponse)
def report(app_id: str, country: str, save_local: bool = False, db: Session = Depends(get_db)):
    m = compute_metrics(db, app_id, country)
    ins = analyze_insights(db, app_id, country)
    # Charts
    # Rating distribution
    fig1 = plt.figure()
    xs = list(m['distribution'].keys())
    ys = list(m['distribution'].values())
    plt.bar(xs, ys)
    plt.title("Rating Distribution (%)")
    plt.xlabel("Stars")
    plt.ylabel("Percent")
    import base64, io
    buf1 = io.BytesIO()
    fig1.savefig(buf1, format='png', bbox_inches='tight'); plt.close(fig1)
    img1 = base64.b64encode(buf1.getvalue()).decode()

    # Sentiment
    fig2 = plt.figure()
    xs2 = list(ins['sentiment_percent'].keys())
    ys2 = list(ins['sentiment_percent'].values())
    plt.bar(xs2, ys2)
    plt.title("Sentiment Distribution (%)")
    plt.xlabel("Sentiment")
    plt.ylabel("Percent")
    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png', bbox_inches='tight'); plt.close(fig2)
    img2 = base64.b64encode(buf2.getvalue()).decode()

    html = f"""
    <html><head><meta charset='utf-8'><title>Report for {app_id} ({country})</title>
    <style>body{{font-family:Arial,Helvetica,sans-serif; margin:24px}} .grid{{display:grid; grid-template-columns:1fr 1fr; gap:24px}}</style>
    </head><body>
    <h1>Apple Store Review Analysis — App {app_id} / {country.upper()}</h1>
    <h2>Metrics</h2>
    <ul>
      <li>Total reviews: <b>{m['count']}</b></li>
      <li>Average rating: <b>{m['average_rating']}</b></li>
    </ul>
    <div class="grid">
      <div><h3>Ratings</h3><img src="data:image/png;base64,{img1}" /></div>
      <div><h3>Sentiment</h3><img src="data:image/png;base64,{img2}" /></div>
    </div>
    <h2>Top Negative Keywords</h2>
    <p>{', '.join(ins['top_negative_keywords']) or '—'}</p>
    <h2>Recommendations</h2>
    <ul>
      {''.join(f'<li>{r}</li>' for r in ins['recommendations'])}
    </ul>
    <p style="margin-top:40px;font-size:12px;color:#666">Generated by Apple Store Review Analysis API</p>
    </body></html>
    """

    if save_local:
        tmp = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
        try:
            tmp.write(html)
        finally:
            tmp.close()
        os.replace(tmp.name, f"report_{app_id}_{country}.html")

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="report_{app_id}_{country}.html"'}
    )