from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class CreateBoardModel(BaseModel):
    board_title: str
    board_description: Optional[str]

class UpdateBoardModel(BaseModel):
    board_title: Optional[str] = None
    board_description: Optional[str] = None
    public: Optional[bool] = False

class UserResponseModel(BaseModel):
    uid: uuid.UUID
    username: str
    created_at: datetime