from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, status, HTTPException, WebSocket, WebSocketDisconnect
from src.websocket_manager import manager
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .schemas import UserCreateModel, UserLoginModel, UserPasswordResetModel
import uuid
from .utils import (
    decode_url_safe_token,
    create_acces_token,
    create_refresh_token,
)
from src.auth.dependencies import AccessTokenBearer
from src.auth.dependencies import RefreshTokenBearer
from src.auth.service import UserService
from datetime import timedelta
from fastapi import status
from src.board.service import BoardService
from src.db.redis import add_jti_to_blocklist
from src.ratelimiter import AuthRateLimiters

auth_ratelimit = AuthRateLimiters()
board_service = BoardService()
user_service = UserService()
auth_router = APIRouter()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()

REFRESH_TOKEN_EXPIRY = 2


@auth_router.post("/create")
async def create_user(
    payload: UserCreateModel,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.create),
):
    user_email = payload.email

    response = await user_service.create_user(payload, session)

    email_response = await user_service.send_verify_account_email(user_email)

    if email_response:
        raise HTTPException(
            detail="Account successfully created and verification email sent.",
            status_code=status.HTTP_201_CREATED,
        )
    else:
        raise HTTPException(
            detail="Account successfully created but verification email failed.",
            status_code=status.HTTP_100_CONTINUE,
        )


@auth_router.post("/login")
async def login_user(
    payload: UserLoginModel,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.login),
):
    user_email = payload.email
    check_user = await user_service.get_user_by_email(user_email, session)

    user_email = check_user.email
    user_uid = str(check_user.uid)
    access_token = create_acces_token(
        user_data={"email": user_email, "user_uid": user_uid}
    )
    refresh_token = create_refresh_token(
        user_data={"email": user_email, "user_uid": user_uid},
        refresh=True,
        expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
    )
    if not refresh_token or not access_token:
        return JSONResponse(
            content={
                "message": "Something went wrong during the creation of tokens.",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return JSONResponse(
        content={
            "message": "Account logged in successfully!",
            "acces_token": access_token,
            "refresh_token": refresh_token,
        },
        status_code=status.HTTP_201_CREATED,
    )


@auth_router.post("/leave", status_code=status.HTTP_200_OK)
async def leave_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.leave),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.user_leave_board(board_uid, user_uid, session)
    return {"message": "The board has been left successfully"}


@auth_router.post("/change_password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: UserPasswordResetModel,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.change_password),
):
    new_password = payload.new_password
    old_password = payload.old_password
    if new_password == old_password:
        raise HTTPException(
            detail="The new password must be different from the old password",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.change_password(new_password, user_uid, session)
    return {"message": "Password changed successfully"}


@auth_router.get("/get-user-boards")  
async def get_user_boards(
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.get_boards),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.get_user_boards(page, size, user_uid, session)
    if not response:
        return None
    return response


@auth_router.get("/get-user-activity")  
async def get_user_activity(
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.get_activity),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.get_user_activity(page, size, user_uid, session)
    if not response:
        return None
    return response


@auth_router.get("/get-user-invites")  
async def get_user_invites(
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.get_invites),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.get_user_invites(page, size, user_uid, session)
    if not response:
        return None
    return response


@auth_router.post("/request/board/{board_uid}", status_code=status.HTTP_200_OK)
async def request_public_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.request_board),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.request_public_board_join(
        user_uid, board_uid, session
    )
    return {"message": "The request has been sent successfully"}


@auth_router.get("/verify/{token}", status_code=status.HTTP_200_OK)
async def verify_user_account(
    token: str,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.verify),
):
    token_data = decode_url_safe_token(token)
    if not token_data:
        return None
    user_email = token_data.get("email")

    response = await user_service.get_user_by_email(user_email, session)
    user_uid = response.uid

    response = await user_service.verify_user_account(user_uid, session)
    if not response:
        return None
    return {"message": "Account verified successfully"}


@auth_router.get("/accept_invite/{token}", status_code=status.HTTP_200_OK)
async def accepted_email_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.accept_invite),
):
    token_data = decode_url_safe_token(token)
    if (
        "email" not in token_data.keys()
        or "board_uid" not in token_data.keys()
        or "user_uid" not in token_data.keys()
        or "target_uid" not in token_data.keys()
    ):
        return None

    user_email = token_data.get("email")
    board_uid = token_data.get("board_uid")
    sender_uid = token_data.get("user_uid")
    reciever_uid = token_data.get("target_uid")

    create_invitation = await user_service.accept_or_reject_invitation(
        user_uid=sender_uid,
        recipient_uid=reciever_uid,
        board_uid=board_uid,
        rejected=False,
        session=session,
    )

    return {"message": "The invitation has been successfully accepted"}


@auth_router.get("/reject_invite/{token}", status_code=status.HTTP_200_OK)
async def rejected_email_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.reject_invite),
):
    token_data = decode_url_safe_token(token)
    if (
        "email" not in token_data.keys()
        or "board_uid" not in token_data.keys()
        or "user_uid" not in token_data.keys()
        or "target_uid" not in token_data.keys()
    ):
        return None

    user_email = token_data.get("email")
    board_uid = token_data.get("board_uid")
    sender_uid = token_data.get("user_uid")
    reciever_uid = token_data.get("target_uid")

    create_invitation = await user_service.accept_or_reject_invitation(
        user_uid=sender_uid,
        recipient_uid=reciever_uid,
        board_uid=board_uid,
        rejected=True,
        session=session,
    )

    return {"message": "The invitation has been successfully rejected"}


@auth_router.get("/me")
async def get_user_info(
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.me),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.get_user_info(user_uid, session)
    return response


@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def revoke_token(
    token_details: dict = Depends(access_token_bearer),
    _rl: None = Depends(auth_ratelimit.revoke_token),
):

    jti = token_details["jti"]

    await add_jti_to_blocklist(jti)

    return {"message": "You have been successfully logged out"}


@auth_router.get("/notifications")  
async def get_user_notifications(
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.notifications),
):

    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.get_user_notifications(page, size, user_uid, session)
    if not response:
        return None
    return response


@auth_router.post("/notification-read", status_code=status.HTTP_200_OK)
async def read_user_notification(
    notification_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.notification_read),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await user_service.read_user_notification(
        user_uid, notification_uid, session
    )
    return {"message": "Notification read successfully"}


@auth_router.post("/notification-readall", status_code=status.HTTP_200_OK)
async def read_all_user_notifications(
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(auth_ratelimit.notification_readall),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    result = await user_service.read_all_user_notifications(user_uid, session)
    if not result:
        return None
    return result

@auth_router.websocket("/ws/{user_uid}")
async def websocket_endpoint(websocket: WebSocket, user_uid: str):
    # register this user as connected
    await manager.connect(user_uid, websocket)
    try:
        while True:
            # this loop keeps the connection alive
            # receive_text() waits for the client to send something
            # your client can send a heartbeat ping every 30 seconds
            # to prevent the connection from timing out
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        # client closed the browser tab, lost internet etc.
        # remove them from active_connections
        manager.disconnect(user_uid)