from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class EmailRecord(Base):
    __tablename__ = "email_records"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String(255), unique=True, index=True)
    subject = Column(String(500))
    sender = Column(String(255))
    body = Column(Text)
    is_spam = Column(Boolean, default=False)
    spam_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)