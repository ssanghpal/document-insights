from pydantic import BaseModel
from typing import Optional

class Document(BaseModel):
    user_id: str
    title: str
    content: str

class DocumentResponse(BaseModel):
    document_id: str
    status: str
    summary: Optional[str] = None