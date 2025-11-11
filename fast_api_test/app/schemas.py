from pydantic import BaseModel


class PostCreate(BaseModel):
    tittle: str
    content: str

class PostResponse(BaseModel):
    tittle: str
    content: str
    
    