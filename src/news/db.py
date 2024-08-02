from sqlalchemy import create_engine, Column, DateTime, String, Date, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import uuid
import os

# Create a SQLAlchemy engine
engine = create_engine(f'postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}')

# Create a base class for declarative class definitions
Base = declarative_base()

# Define your SQLAlchemy model
class NewsModel(Base):
    __tablename__ = 'news'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String)
    url = Column(String)
    transcript = Column(Text)
    channel = Column(String)
    publication_date = Column(Date)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)
    summary_updated_at = Column(DateTime)

    __table_args__ = (UniqueConstraint('url', name='unique_url'), )

# Create the table in the database
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
