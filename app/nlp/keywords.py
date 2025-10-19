from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer

def top_keywords(texts: List[str], top_k: int = 15) -> List[str]:
    if not texts:
        return []
    vec = TfidfVectorizer(ngram_range=(1,2), max_features=500, min_df=1, stop_words='english')
    X = vec.fit_transform(texts)
    # Compute mean tf-idf across documents
    means = X.mean(axis=0).A1
    feats = vec.get_feature_names_out()
    pairs = sorted(zip(means, feats), reverse=True)[:top_k]
    return [t for _, t in pairs]
