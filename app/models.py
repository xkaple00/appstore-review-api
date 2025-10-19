from sqlalchemy import Column, Integer, String, DateTime, Float, Text, UniqueConstraint
from .database import Base

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String, index=True, nullable=False)
    country = Column(String, index=True, nullable=False)
    review_id = Column(String, nullable=False)
    author = Column(String, default="")
    title = Column(String, default="")
    text = Column(Text, default="")
    rating = Column(Integer, nullable=False)
    version = Column(String, default="")
    date = Column(DateTime, nullable=True)
    source = Column(String, default="")
    language = Column(String, default="")
    __table_args__ = (UniqueConstraint('app_id','country','review_id', name='_app_country_review_uc'),)
