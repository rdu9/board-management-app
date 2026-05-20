import time
import logging
from fastapi import Depends, Request, HTTPException
from src.db.redis import token_blocklist as redis_client
from src.auth.dependencies import AccessTokenBearer

logger = logging.getLogger(__name__)

async def get_rate_limit_key(request: Request) -> str:
    token = request.headers.get("Authorization")
    if token:
        try:
            token_details = await AccessTokenBearer()(request)
            return token_details["user"]["user_uid"]
        except:
            pass
    return request.client.host

async def check_rate_limit(key: str, limit: int, window: int) -> tuple[bool , int , int]:

    now = time.time()

    window_start = now - window

    pipe = redis_client.pipeline()

    pipe.zremrangebyscore(key, 0 , window_start)
    pipe.zcard(key)
    pipe.zadd(key, {f"{now}": now})
    pipe.expire(key, window)

    results = await pipe.execute()

    current_count = results[1]

    if current_count >= limit:

        oldest = await redis_client.zrange(key, 0 , 0 , withscores=True)

        retry_after = (
            int(oldest[0][1] + window - now) + 1
            if oldest else window
        )
        return False, 0 , max(retry_after,1)
    return True, limit - current_count - 1 , 0

class RateLimiter:

    def __init__(self, requests: int, window: int, endpoint: str):
        self.requests = requests
        self.window = window
        self.endpoint = endpoint

    async def __call__(self, request: Request, user_uid: str = Depends(get_rate_limit_key)):
        
        key = f"ratelimit:{self.endpoint}:{user_uid}"

        try:
            allowed,remaining,retry_after = await check_rate_limit(key, self.requests , self.window)
        except Exception as e:
            logger.error("Rate limiter redis error - failing open: %s", e , exc_info=True)
            return
        
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = self.requests
        
        if not allowed:
            logger.warning("Rate limit exceeded | key=%s | retry_after=%ss", key,retry_after)

            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Too many requests. Please slow down.",
                    "error_code": "rate_limit_exceeded",
                    "retry_after_seconds": retry_after
                },
                headers={
                    "Retry_After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time())+retry_after)
                }
            )
        
# auth / users


class AuthRateLimiters:
    create = RateLimiter(requests=3, window=3600, endpoint="user_create")
    login = RateLimiter(requests=5, window=60, endpoint="user_login")
    logout = RateLimiter(requests=10, window=60, endpoint="user_logout")
    change_password = RateLimiter(requests=3, window=3600, endpoint="user_change_password")
    leave = RateLimiter(requests=5, window=60, endpoint="user_leave")
    me = RateLimiter(requests=60, window=60, endpoint="user_me")
    get_boards = RateLimiter(requests=30, window=60, endpoint="user_get_boards")
    get_activity = RateLimiter(requests=20, window=60, endpoint="user_get_activity")
    get_invites = RateLimiter(requests=30, window=60, endpoint="user_get_invites")
    notifications = RateLimiter(requests=60, window=60, endpoint="user_notifications")
    notification_read = RateLimiter(requests=30, window=60, endpoint="user_notification_read")
    notification_readall = RateLimiter(requests=10, window=60, endpoint="user_notification_readall")
    request_board = RateLimiter(requests=5, window=60, endpoint="user_request_board")
    verify = RateLimiter(requests=5, window=3600, endpoint="user_verify")
    accept_invite = RateLimiter(requests=10, window=60, endpoint="user_accept_invite")
    reject_invite = RateLimiter(requests=10, window=60, endpoint="user_reject_invite")
    me = RateLimiter(requests=60, window=60, endpoint="user_me")
    revoke_token = RateLimiter(requests=10, window=60, endpoint="user_revoke_token")
    notifications = RateLimiter(requests=60, window=60, endpoint="user_notifications")
    notification_read = RateLimiter(requests=30, window=60, endpoint="user_notification_read")
    notification_readall = RateLimiter(requests=10, window=60, endpoint="user_notification_readall")


class BoardRateLimiters:
    create = RateLimiter(requests=10, window=3600, endpoint="board_create")
    delete = RateLimiter(requests=5, window=3600, endpoint="board_delete")
    update = RateLimiter(requests=20, window=60, endpoint="board_update")
    archive = RateLimiter(requests=5, window=60, endpoint="board_archive")
    unarchive = RateLimiter(requests=5, window=60, endpoint="board_unarchive")
    duplicate = RateLimiter(requests=5, window=3600, endpoint="board_duplicate")
    members = RateLimiter(requests=30, window=60, endpoint="board_members")
    member_update = RateLimiter(requests=10, window=60, endpoint="board_member_update")
    member_remove = RateLimiter(requests=10, window=60, endpoint="board_member_remove")
    invite = RateLimiter(requests=10, window=60, endpoint="board_invite")
    pending_requests = RateLimiter(requests=30, window=60, endpoint="board_pending_requests")
    approve_request = RateLimiter(requests=10, window=60, endpoint="board_approve_request")
    reject_request = RateLimiter(requests=10, window=60, endpoint="board_reject_request")
    audit = RateLimiter(requests=20, window=60, endpoint="board_audit")
    details = RateLimiter(requests=60, window=60, endpoint="board_details")
    make_public = RateLimiter(requests=5, window=60, endpoint="board_make_public")
    make_private = RateLimiter(requests=5, window=60, endpoint="board_make_private")
    user_info = RateLimiter(requests=30, window=60, endpoint="board_user_info")
    public = RateLimiter(requests=30, window=60, endpoint="board_public")
    search = RateLimiter(requests=20, window=60, endpoint="board_search")
    search_users = RateLimiter(requests=20, window=60, endpoint="board_search_users")
    notify_user = RateLimiter(requests=10, window=60, endpoint="board_notify_user")
    notify_all_users = RateLimiter(requests=3, window=60, endpoint="board_notify_all_users")