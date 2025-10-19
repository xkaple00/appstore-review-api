import requests, datetime as dt
from typing import List, Dict
from ..utils.text import clean_text

RSS_TMPL = "https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"

class RSSCollector:
    def fetch(self, app_id: str, country: str, max_pages: int = 5) -> List[Dict]:
        out = []
        for page in range(1, max_pages+1):
            url = RSS_TMPL.format(country=country, page=page, app_id=app_id)
            try:
                r = requests.get(url, timeout=15)
                if r.status_code != 200:
                    continue
                data = r.json()
                entries = data.get('feed',{}).get('entry',[])
                # The first entry can be app metadata, skip non-reviews
                for e in entries:
                    if 'im:rating' not in e:
                        continue
                    rid = e.get('id',{}).get('label',"")
                    title = e.get('title',{}).get('label',"")
                    text = e.get('content',{}).get('label',"")
                    rating = int(e.get('im:rating',{}).get('label',0))
                    author = e.get('author',{}).get('name',{}).get('label',"")
                    version = e.get('im:version',{}).get('label',"")
                    date_label = e.get('updated',{}).get('label',"") or e.get('updated',"")
                    try:
                        date = dt.datetime.fromisoformat(date_label.replace('Z','+00:00')) if date_label else None
                    except Exception:
                        date = None
                    out.append({
                        "review_id": str(rid),
                        "author": author,
                        "title": clean_text(title),
                        "text": clean_text(text),
                        "rating": rating,
                        "version": version,
                        "date": date,
                        "source": "rss",
                        "language": ""
                    })
            except Exception:
                continue
        return out
