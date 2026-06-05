from fastapi import APIRouter, Depends, status
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid
from src.auth.dependencies import AccessTokenBearer
from src.auth.dependencies import RefreshTokenBearer
from src.board.service import BoardService
from src.db.models import UserRole
from src.board.schemas import CreateBoardModel, UpdateBoardModel
from src.auth.service import UserService
from src.board.schemas import UserResponseModel
from src.ratelimiter import BoardRateLimiters

board_ratelimit = BoardRateLimiters()
board_service = BoardService()
user_service = UserService()
board_router = APIRouter()
access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()


@board_router.get("/members", status_code=status.HTTP_200_OK)
async def board_members(
    board_uid: uuid.UUID,
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.members),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.board_members(
        page, size, board_uid, user_uid, session
    )
    if not response:
        return None
    return response


@board_router.post("/member-update", status_code=status.HTTP_200_OK)
async def update_board_member_roles(
    payload: UserRole,
    board_uid: uuid.UUID,
    user_to_update_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.member_update),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.update_board_member_roles(
        payload, board_uid, user_uid, user_to_update_uid, session
    )
    return {"message": "Roles updated successfully"}


@board_router.post("/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.duplicate),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.duplicate_board(board_uid, user_uid, session)
    return {"message": "Board duplicated successfully"}


@board_router.post("/archive", status_code=status.HTTP_201_CREATED)
async def archive_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.archive),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.archive_board(board_uid, user_uid, session)
    return {"message": "Board archived successfully"}


@board_router.post("/invite", status_code=status.HTTP_200_OK)
async def send_board_invite(
    board_uid: uuid.UUID,
    target_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.invite),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])

    # the several checks

    user_email = await user_service.get_email_by_uid(target_uid, session)

    check_board = await board_service.get_board_by_uid(board_uid, session)

    check_for_permission = await board_service.board_admin_check(
        board_uid, user_uid, session
    )

    user_in_board = await user_service.check_if_user_is_in_board(
        target_uid, board_uid, session
    )

    send_invite = await user_service.send_board_invite(
        user_uid, target_uid, user_email, board_uid, session
    )

    return {"message": "The invitation was sent successfully!"}


@board_router.get("/pending-requests", status_code=status.HTTP_200_OK)
async def see_board_pending_requests(
    board_uid: uuid.UUID,
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.pending_requests),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.see_board_pending_requests(
        board_uid, user_uid, session
    )
    return response


@board_router.get("/audit", status_code=status.HTTP_200_OK)
async def board_audit(
    board_uid: uuid.UUID,
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.audit),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.board_audit(page, size, board_uid, user_uid, session)
    if not response:
        return None
    return response


@board_router.post("/join-request-approve", status_code=status.HTTP_200_OK)
async def approve_join_request(
    board_uid: uuid.UUID,
    target_user_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.approve_request),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.approve_join_request(
        board_uid, user_uid, target_user_uid, session
    )
    return {"message": "Request was approved successfully"}


@board_router.post("/join-request-reject", status_code=status.HTTP_200_OK)
async def reject_join_request(
    board_uid: uuid.UUID,
    target_user_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.reject_request),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.reject_join_request(
        board_uid, user_uid, target_user_uid, session
    )
    return {"message": "Request was rejected successfully"}


@board_router.delete("/delete", status_code=status.HTTP_200_OK)
async def delete_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.delete),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.delete_board(board_uid, user_uid, session)
    return {"message": "The board has been deleted successfully"}


@board_router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_board(
    payload: CreateBoardModel,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.create),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.create_board(payload, user_uid, session)
    return {"message": "The board has been craeted successfully"}


@board_router.post("/update", status_code=status.HTTP_201_CREATED)
async def update_board(
    payload: UpdateBoardModel,
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.update),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.update_board(payload, user_uid, board_uid, session)
    return {"message": "The board was updated successfully"}


@board_router.post("/member-remove", status_code=status.HTTP_201_CREATED)
async def remove_member(
    member_to_remove_uid: uuid.UUID,
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.member_remove),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.remove_member(
        user_uid, member_to_remove_uid, board_uid, session
    )
    return {"message": "Member was removed successfully"}


@board_router.post("/make-public", status_code=status.HTTP_200_OK)
async def make_board_public(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.make_public),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.make_board_public_or_private(
        board_uid=board_uid, user_uid=user_uid, public=True, session=session
    )
    if not response:
        return None
    return {"message": "The board was made public successfully"}


@board_router.post("/make-private", status_code=status.HTTP_200_OK)
async def make_board_private(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.make_private),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.make_board_public_or_private(
        board_uid=board_uid, user_uid=user_uid, public=False, session=session
    )
    return {"message": "The board was made private successfully"}


@board_router.get("/details", status_code=status.HTTP_200_OK)
async def get_board_details(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.details),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.get_board_details(board_uid, user_uid, session)
    return response


@board_router.post("/unarchive", status_code=status.HTTP_200_OK)
async def unarchive_board(
    board_uid: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.unarchive),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.unarchive_board(board_uid, user_uid, session)
    return {"message": "The board was unarchived successfully"}


@board_router.get("/user-info", status_code=status.HTTP_200_OK)
async def get_user_info_from_board(
    board_uid: uuid.UUID,
    target_user: uuid.UUID,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.user_info),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.get_user_info_from_board(
        board_uid, user_uid, target_user, session
    )
    return response


@board_router.get("/public", status_code=status.HTTP_200_OK)
async def get_public_boards(
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.public),
):
    response = await board_service.get_all_public_board(page, size, session)
    if not response:
        return None
    return response


@board_router.get("/search", status_code=status.HTTP_200_OK)
async def search_boards(
    q: str,
    page: int = 1,
    size: int = 20,
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.search),
):
    response = await board_service.search_boards(q, page, size, session)
    if not response:
        return None
    return response


@board_router.get(
    "/search-users",
    response_model=list[UserResponseModel],
    status_code=status.HTTP_200_OK,
)
async def search_users(
    q: str,
    board_uid: uuid.UUID,
    page: int = 1,
    size: int = 20,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.search_users),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.search_users_to_invite(
        q, board_uid, page, size, session
    )
    if not response:
        return None
    return response


@board_router.post("/notify-user", status_code=status.HTTP_200_OK)
async def notify_user_from_board(
    target_uid: uuid.UUID,
    board_uid: uuid.UUID,
    message_content: str = None,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
    _rl: None = Depends(board_ratelimit.notify_user),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.notify_board_user(
        user_uid, target_uid, board_uid, session, message_content
    )
    return {"message": "The user was notified successfully"}


@board_router.post("/notify-all-users", status_code=status.HTTP_200_OK)
async def notify_all_board_users(
    board_uid: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
    message_content: str = None,
    _rl: None = Depends(board_ratelimit.notify_all_users),
):
    user_uid = uuid.UUID(token_details.get("user")["user_uid"])
    response = await board_service.notify_all_board_users(
        user_uid, board_uid, session, message_content
    )
    if not response:
        return None
    return {"message": "All users have been notified successfully"}
