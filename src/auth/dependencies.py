from fastapi import Request
from fastapi.security.http import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from .utils import decode_token
from .service import UserService
from src.db.redis import token_in_blocklist


user_service = UserService()


class TokenBearer(HTTPBearer):

    def __init__(self, auto_error=True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:

        creds = await super().__call__(request)

        token = creds.credentials

        token_data = decode_token(token)

        if not token_data:
            return None
        
        if await token_in_blocklist(token_data["jti"]):
            return None

        self.verify_token_data(token_data)

        return token_data

    def verify_token_data(self, token_data):
        raise NotImplemented("Please override this with a child class")


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data and token_data['refresh']:
            return None
        
class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data and not token_data['refresh']:
            return None 
        