from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class CollectRequest(BaseModel):
    app_id: str = Field(..., description="Numeric Apple App Store ID (e.g., '310633997')")
    country: str = Field(default="us", description="2-letter country code")
    how_many: int = Field(default=100, ge=1, le=1000)
    source: str = Field(default="auto", description="auto|webscraper|rss|connect")

class ReviewOut(BaseModel):
    app_id: str
    country: str
    review_id: str
    author: Optional[str] = ""
    title: Optional[str] = ""
    text: Optional[str] = ""
    rating: int
    version: Optional[str] = ""
    date: Optional[datetime] = None
    source: Optional[str] = ""
    language: Optional[str] = ""

class MetricsOut(BaseModel):
    app_id: str
    country: str
    count: int
    average_rating: float
    distribution: Dict[str, float]

class InsightsOut(BaseModel):
    app_id: str
    country: str
    sentiment_counts: Dict[str, int]
    sentiment_percent: Dict[str, float]
    top_negative_keywords: List[str]
    recommendations: List[str]
