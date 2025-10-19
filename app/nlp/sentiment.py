from transformers import pipeline
import threading

_LOCK = threading.Lock()
_pipe = None

def _get_pipe(model_name="cardiffnlp/twitter-roberta-base-sentiment-latest"):
    global _pipe
    with _LOCK:
        if _pipe is None:
            _pipe = pipeline("sentiment-analysis", model=model_name)
    return _pipe

def classify_sentiment(text: str) -> str:
    if not text:
        return "neutral"
    pred = _get_pipe()(text[:])[0]  # {'label': 'positive/negative/neutral' or 'LABEL_0/1/2'}
    lab = pred["label"].lower()
    if "neg" in lab or lab.endswith("_0"):  # be robust to label schemes
        return "negative"
    if "pos" in lab or lab.endswith("_2"):
        return "positive"
    return "neutral"
