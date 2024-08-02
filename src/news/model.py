from pydantic import BaseModel, UUID4, Field
from datetime import datetime, date

class News(BaseModel):
    id: UUID4 = None
    title: str
    url: str
    transcript: str
    channel: str
    publication_date: date
    category: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_updated_at(self):
        self.updated_at = datetime.utcnow()

    def dict(self, *args, **kwargs):
        result = super().dict(*args, **kwargs)
        return result
    
    class Config:
        orm_mode = True