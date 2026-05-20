from src.db.models import (
    User,
    Request,
    BoardUser,
    Board,
    Audit,
    Notification,
)
from sqlalchemy import or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid
from src.db.models import UserRole, AuditAction, RequestStatus, NotificationType
from typing import Optional
from .schemas import CreateBoardModel, UpdateBoardModel
from src.websocket_manager import manager
from src.errors import (
    RequestNotFound,
    BoardUserNotFound,
    UserNotInBoard,
    InsufficientPermission,
    BoardNotFound,
    UserNotFound,
    InvalidInput,
)

class BoardService:

    def log_board_action(
        self,
        user_uid: uuid.UUID,
        board_uid: uuid.UUID,
        action: AuditAction,
        session: AsyncSession,
        target_uid: Optional[uuid.UUID] = None,
    ):
        new_audit = Audit(
            user_uid=user_uid,
            board_uid=board_uid,
            target_uid=target_uid if target_uid else None,
            action=action,
        )
        session.add(new_audit)
        return new_audit

    async def send_notification(
        self,
        user_uid: uuid.UUID,
        board_uid: uuid.UUID,
        message_type: NotificationType,
        session: AsyncSession,
        message_content: str = None,
        is_read: bool = False,
    ):
        new_notification = Notification(
            user_uid=user_uid,
            board_uid=board_uid,
            message_type=message_type,
            message_content=message_content,
            is_read=is_read,
        )
        session.add(new_notification)

        await manager.send_notification_websocket(
            user_uid=str(user_uid),
            message={
                "type": "notification",
                "message_type": message_type.value,
                "board_uid": str(board_uid),
                "message_content": message_content,
            },
        )

        return new_notification

    async def get_board_by_uid(self, board_uid: uuid.UUID, session: AsyncSession):
        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        return result_first

    async def board_admin_check(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Board, BoardUser)
            .outerjoin(
                BoardUser,
                (BoardUser.board_uid == board_uid) & (BoardUser.user_uid == user_uid),
            )
            .where(Board.uid == board_uid)
        )
        result = await session.execute(statement)
        row = result.one_or_none()
        if not row:
            raise InvalidInput()

        board, board_user = row

        is_owner = board.owner_uid == user_uid
        is_admin = board_user is not None and board_user.role == UserRole.ADMIN
        if not (is_owner or is_admin):
            raise InsufficientPermission()
        return board

    async def board_members(
        self,
        page: int,
        size: int,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        session: AsyncSession,
    ):
        result = await session.exec(
            select(BoardUser)
            .where(BoardUser.board_uid == board_uid)
            .limit(size)
            .offset((page - 1) * size)
        )
        members = result.all()

        if not members:
            raise BoardNotFound()

        if not any(m.user_uid == user_uid for m in members):
            raise BoardUserNotFound()

        return members

    async def update_board_member_roles(
        self,
        payload: UserRole,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        user_to_update_uid: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(BoardUser).where(
            BoardUser.user_uid == user_to_update_uid, BoardUser.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardUserNotFound()

        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.MEMBER_ROLE_CHANGED,
            session=session,
            target_uid=user_to_update_uid,
        )

        await self.send_notification(
            user_uid=user_to_update_uid,
            board_uid=board_uid,
            message_type=NotificationType.ROLE_CHANGED,
            session=session,
            message_content=f"Your role has been changed by user {user_uid}",
            is_read=False,
        )

        result_first.role = payload
        await session.commit()
        return result_first

    async def duplicate_board(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        new_board = Board(
            owner_uid=user_uid,
            board_title=f"{result_first.board_title} ( Copy )",
            board_description=result_first.board_description,
            archived=result_first.archived,
            public=result_first.public,
        )

        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.BOARD_DUPLICATED,
            session=session,
        )

        session.add(new_board)
        await session.commit()
        return new_board

    async def archive_board(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        result_first.archived = True

        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.BOARD_ARCHIVED,
            session=session,
        )

        await session.commit()
        return True

    async def see_board_pending_requests(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Request).where(
            Request.board_uid == board_uid, Request.status == RequestStatus.PENDING
        )
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def board_audit(
        self,
        page: int,
        size: int,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = (
            select(Audit).where(Audit.board_uid == board_uid).offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def approve_join_request(
        self,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        target_user_uid: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Request).where(
            Request.board_uid == board_uid, Request.user_uid == target_user_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise RequestNotFound()

        result_first.status = RequestStatus.APPROVED

        new_board = BoardUser(
            user_uid=target_user_uid, board_uid=board_uid, role=UserRole.MEMBER
        )

        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.REQUEST_APPROVED,
            session=session,
        )
        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.MEMBER_ADDED,
            session=session,
        )

        session.add(new_board)

        await self.send_notification(
            user_uid=target_user_uid,
            board_uid=board_uid,
            message_type=NotificationType.REQUEST_APPROVED,
            session=session,
        )

        await session.commit()
        return new_board

    async def reject_join_request(
        self,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        target_user_uid: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Request).where(
            Request.board_uid == board_uid, Request.user_uid == target_user_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise RequestNotFound()

        result_first.status = RequestStatus.REJECTED

        self.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.REQUEST_REJECTED,
            session=session,
        )

        await self.send_notification(
            user_uid=target_user_uid,
            board_uid=board_uid,
            message_type=NotificationType.REQUEST_REJECTED,
            session=session,
        )

        await session.commit()
        return True

    async def delete_board(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        await session.delete(result_first)

        self.log_board_action(
            board_uid=board_uid,
            user_uid=user_uid,
            action=AuditAction.BOARD_DELETED,
            session=session,
        )

        await session.commit()
        return {}

    async def create_board(
        self, payload: CreateBoardModel, user_uid: uuid.UUID, session: AsyncSession
    ):
        board_data_dict = payload.model_dump()
        new_board = Board(**board_data_dict)
        new_board.owner_uid = user_uid

        session.add(new_board)
        await session.commit()
        await session.refresh(new_board)

        board_uid = new_board.uid

        new_board_user = BoardUser(
            user_uid=user_uid,
            board_uid=board_uid,
            role=UserRole.OWNER,
        )

        self.log_board_action(
            board_uid=board_uid,
            user_uid=user_uid,
            action=AuditAction.BOARD_CREATED,
            session=session,
        )

        session.add(new_board)
        session.add(new_board_user)
        await session.commit()
        return new_board

    async def update_board(
        self,
        payload: UpdateBoardModel,
        user_uid: uuid.UUID,
        board_uid: uuid.UUID,
        session: AsyncSession,
    ):

        await self.board_admin_check(board_uid, user_uid, session)

        update_data = payload.model_dump(exclude_unset=True)

        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()

        for i, j in update_data.items():
            setattr(result_first, i, j)

        await session.commit()
        await session.refresh(result_first)

        return result_first

    async def remove_member(
        self,
        user_uid: uuid.UUID,
        member_to_remove_uid: uuid.UUID,
        board_uid: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(BoardUser).where(
            BoardUser.user_uid == member_to_remove_uid,
            BoardUser.board_uid == board_uid,
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardUserNotFound()

        self.log_board_action(
            board_uid=board_uid,
            user_uid=user_uid,
            action=AuditAction.MEMBER_REMOVED,
            session=session,
        )

        await session.delete(result_first)

        await self.send_notification(
            user_uid=member_to_remove_uid,
            board_uid=board_uid,
            message_type=NotificationType.MEMBER_REMOVED,
            session=session,
        )

        await session.commit()
        return {}

    async def add_user_from_email(
        self, user_email: str, board_uid: uuid.UUID, session: AsyncSession
    ):
        from src.auth.service import UserService

        user_service = UserService()

        user = await user_service.get_user_by_email(user_email, session)
        if not user:
            raise UserNotFound()

        user_uid = user.uid

        new_board_user = BoardUser(
            user_uid=user_uid,
            board_uid=board_uid,
        )

        session.add(new_board_user)
        await session.commit()
        return new_board_user

    async def make_board_public_or_private(
        self,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        public: bool,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        match public:
            case True:
                result_first.public = True
                await session.commit()
                return True
            case False:
                result_first.public = False
                await session.commit()
                return True

    async def get_board_details(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Board).where(Board.uid == board_uid)
        result = await session.exec(statement)
        board = result.one_or_none()
        if not board:
            raise BoardNotFound()

        board_private = board.public == False

        match board_private:
            case True:
                await self.board_admin_check(board_uid, user_uid, session)
                return board

            case False:

                return board

    async def unarchive_board(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Board).where(Board.uid == board_uid, Board.archived == True)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise BoardNotFound()

        result_first.archived = False
        await session.commit()
        return True

    async def get_user_info_from_board(
        self,
        board_uid: uuid.UUID,
        user_uid: uuid.UUID,
        target_user: uuid.UUID,
        session: AsyncSession,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = (
            select(User, BoardUser)
            .join(BoardUser, BoardUser.user_uid == target_user)
            .where(User.uid == target_user)
            .where(BoardUser.board_uid == board_uid)
        )
        result = await session.execute(statement)
        row = result.one_or_none()
        if not row:
            raise InvalidInput()

        user, board_user = row

        user_info_dict = {
            "uid": user.uid,
            "username": user.username,
            "created_at": user.created_at,
            "role": board_user.role,
        }

        return user_info_dict

    async def get_all_public_board(self, page: int, size: int, session: AsyncSession):
        statement = select(Board).where(Board.public == True).offset((page - 1) * size)
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def search_boards(
        self, query: str, page: int, size: int, session: AsyncSession
    ):
        statement = (
            select(Board)
            .where(
                Board.archived == False,
                Board.public == True,
                or_(
                    Board.board_title.ilike(f"%{query}%"),
                    Board.board_description.ilike(f"%{query}%"),
                ),
            )
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def search_users_to_invite(
        self,
        query: str,
        board_uid: uuid.UUID,
        page: int,
        size: int,
        session: AsyncSession,
    ):
        existing_members = select(BoardUser.user_uid).where(
            BoardUser.board_uid == board_uid
        )
        statement = (
            select(User)
            .where(
                or_(
                    User.username.ilike(f"%{query}%"),
                    User.first_name.ilike(f"%{query}%"),
                    User.last_name.ilike(f"%{query}%"),
                ),
                User.uid.not_in(existing_members),
            )
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def notify_board_user(
        self,
        user_uid: uuid.UUID,
        target_uid: uuid.UUID,
        board_uid: uuid.UUID,
        session: AsyncSession,
        message_content: str = None,
    ):

        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(BoardUser).where(
            BoardUser.user_uid == target_uid, BoardUser.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            raise UserNotInBoard()

        await self.send_notification(
            user_uid=target_uid,
            board_uid=board_uid,
            message_type=NotificationType.MESSAGE_RECEIVED,
            session=session,
            message_content=message_content,
        )

        await session.commit()

        return True

    async def notify_all_board_users(
        self,
        user_uid: uuid.UUID,
        board_uid: uuid.UUID,
        session: AsyncSession,
        message_content: str = None,
    ):
        await self.board_admin_check(board_uid, user_uid, session)

        statement = select(BoardUser).where(BoardUser.board_uid == board_uid)
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None

        user_uids = [m.user_uid for m in result_all if m.role == UserRole.MEMBER]

        for i in user_uids:
            await self.send_notification(
                user_uid=i,
                board_uid=board_uid,
                message_content=message_content,
                message_type=NotificationType.MESSAGE_RECEIVED,
                is_read=False,
                session=session,
            )

        await session.commit()
        return True
