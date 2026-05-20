from pydantic import BaseModel

class UserCreateModel(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name: str

class UserLoginModel(BaseModel):
    email: str
    password: str

class UserPasswordResetModel(BaseModel):
    old_password: str
    new_password: str