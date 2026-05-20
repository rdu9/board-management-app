from src.db.models import (
    User,
    Request,
    UserRole,
    Board,
    BoardUser,
    Audit,
    Invitation,
    Notification,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, update
from .utils import generate_passwwd_hash, create_url_safe_token
import uuid
from .schemas import UserCreateModel
from src.db.models import AuditAction, NotificationType
from src.celery_tasks import send_email
from src.config import Config
from src.errors import (
    RequestNotFound,
    NotificationNotFound,
    InvitationNotFound,
    BoardUserNotFound,
    UserNotInBoard,
    UserAlreadyExists,
    BoardNotFound,
    UserNotFound,
    InvalidInput,
)


class UserService:

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            raise UserNotFound()
        return result_first

    async def check_if_user_is_in_board(
        self, user_uid: uuid.UUID, board_uid: uuid.UUID, session
    ):
        statement = select(BoardUser).where(
            BoardUser.user_uid == user_uid, BoardUser.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.first()
        if result_first:
            return True
        else:
            return None

    async def get_email_by_uid(self, user_uid: uuid.UUID, session: AsyncSession):
        statement = select(User).where(User.uid == user_uid)
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise InvalidInput()
        user_email = result_first.email
        return user_email

    async def user_exists(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            return False
        return True

    async def create_user(self, payload: UserCreateModel, session: AsyncSession):
        user_email = payload.email
        if await self.user_exists(user_email, session):
            raise UserAlreadyExists()

        user_model_dict = payload.model_dump()
        new_user = User(**user_model_dict)

        user_password = payload.password
        hashed_password = generate_passwwd_hash(user_password)
        new_user.password_hash = hashed_password

        session.add(new_user)
        await session.commit()
        return new_user

    async def user_leave_board(
        self, board_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(BoardUser).where(
            BoardUser.user_uid == user_uid, BoardUser.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise UserNotInBoard()

        from src.board.service import BoardService

        board_service = BoardService()
        board_service.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.MEMBER_LEFT,
            session=session,
        )

        await session.delete(result_first)
        await session.commit()
        return {}

    async def change_password(
        self, new_password: str, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(User).where(User.uid == user_uid)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            raise UserNotFound()

        new_hash = generate_passwwd_hash(new_password)
        result_first.password_hash = new_hash
        await session.commit()
        return True

    async def get_user_boards(
        self, page: int, size: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Board)
            .join(BoardUser, BoardUser.board_uid == Board.uid)
            .where(BoardUser.user_uid == user_uid)
            .where(Board.archived == False)
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_all = result.all()
        if not result_all:
            return None
        return result_all

    async def get_user_activity(
        self, page: int, size: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Audit)
            .where(Audit.user_uid == user_uid)
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_first = result.all()
        if not result_first:
            return None
        return result_first

    async def get_user_invites(
        self, page: int, size: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Invitation)
            .where(Invitation.recipient_uid == user_uid)
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_first = result.all()
        if not result_first:
            return None
        return result_first

    async def accept_user_invite(
        self, user_uid: uuid.UUID, board_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Invitation).where(
            Invitation.user_uid == user_uid, Invitation.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise InvitationNotFound()

        second_result = await session.exec(
            select(BoardUser).where(
                BoardUser.user_uid == user_uid, BoardUser.board_uid == board_uid
            )
        )
        check_user = second_result.first()
        if check_user:
            raise BoardUserNotFound()

        result_first.accepted = True
        new_board_user = BoardUser(
            user_uid=user_uid, board_uid=board_uid, role=UserRole.MEMBER
        )

        from src.board.service import BoardService

        board_service = BoardService()
        board_service.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.INVITE_ACCEPTED,
            session=session,
        )
        board_service.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.MEMBER_ADDED,
            session=session,
        )

        session.add(new_board_user)
        await session.commit()
        return new_board_user

    async def reject_user_invite(
        self, user_uid: uuid.UUID, board_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Invitation).where(
            Invitation.user_uid == user_uid, Invitation.board_uid == board_uid
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise InvitationNotFound()

        from src.board.service import BoardService

        board_service = BoardService()
        board_service.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.INVITE_REVOKED,
            session=session,
        )

        await session.delete(result_first)
        await session.commit()
        return {}

    async def get_user_notifications(
        self, page: int, size: int, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = (
            select(Notification)
            .where(Notification.user_uid == user_uid)
            .limit(size)
            .offset((page - 1) * size)
        )
        result = await session.exec(statement)
        result_first = result.all()
        if not result_first:
            return None
        return result_first

    async def read_user_notification(
        self, notification_uid: uuid.UUID, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Notification).where(
            Notification.user_uid == user_uid,
            Notification.uid == notification_uid,
            Notification.is_read == False,
        )
        result = await session.exec(statement)
        result_first = result.one_or_none()
        if not result_first:
            raise NotificationNotFound()
        result_first.is_read = True
        await session.commit()
        return True

    async def read_all_user_notifications(
        self, user_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Notification).where(Notification.user_uid == user_uid)
        result = await session.exec(statement)
        notifications = result.all()
        if not notifications:
            return None

        for notification in notifications:
            notification.is_read = True

        await session.commit()
        return notifications

    async def request_public_board_join(
        self, user_uid: uuid.UUID, board_uid: uuid.UUID, session: AsyncSession
    ):
        statement = select(Board).where(
            Board.uid == board_uid, Board.public == True, Board.archived == False
        )
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            raise BoardNotFound()

        second_result = await session.exec(
            select(BoardUser).where(
                BoardUser.user_uid == user_uid, BoardUser.board_uid == board_uid
            )
        )
        check_user = second_result.first()
        if check_user:
            raise BoardUserNotFound()

        third_result = await session.exec(
            select(Request).where(
                Request.user_uid == user_uid, Request.board_uid == board_uid
            )
        )
        check_request = third_result.first()
        if check_request:
            raise RequestNotFound()

        new_request = Request(user_uid=user_uid, board_uid=board_uid)

        from src.board.service import BoardService

        board_service = BoardService()
        board_service.log_board_action(
            user_uid=user_uid,
            board_uid=board_uid,
            action=AuditAction.REQUEST_SENT,
            session=session,
        )

        session.add(new_request)

        owner_uid = result_first.owner_uid

        await board_service.send_notification(
            user_uid=owner_uid,
            board_uid=board_uid,
            message_type=NotificationType.REQUEST_RECEIVED,
            session=session,
        )

        await session.commit()
        return new_request

    async def verify_user_account(self, user_uid: uuid.UUID, session: AsyncSession):
        statement = select(User).where(User.uid == user_uid)
        result = await session.exec(statement)
        user = result.one_or_none()
        if not user:
            raise UserNotFound()
        user.is_verified = True
        await session.commit()
        return user

    async def send_board_invite(
        self,
        user_uid: uuid.UUID,
        target_uid: uuid.UUID,
        user_email: str,
        board_uid: uuid.UUID,
        session: AsyncSession,
    ):
        first_invitation = Invitation(
            user_uid=user_uid,
            recipient_uid=target_uid,
            board_uid=board_uid,
            accepted=False,
        )

        session.add(first_invitation)

        token = create_url_safe_token(
            {
                "email": user_email,
                "board_uid": str(board_uid),
                "user_uid": str(user_uid),
                "target_uid": str(target_uid),
            }
        )
        link_accept = f"http://{Config.DOMAIN}/api/v1/users/accept_invite/{token}"
        link_reject = f"http://{Config.DOMAIN}/api/v1/users/reject_invite/{token}"

        html_message = f"""
        <h1> You received an invite to the board {board_uid} </h1>
        <p> Please click this <a href="{link_accept}">link</a> to accept this invite </p>
        <p> Please click this <a href="{link_reject}">link</a> to reject this invite </p>
        """

        emails = [user_email]
        subject = "A new board invitation!"
        send_email.delay(emails, subject=subject, body=html_message)

        from src.board.service import BoardService

        board_service = BoardService()

        await board_service.send_notification(
            user_uid=target_uid,
            board_uid=board_uid,
            message_type=NotificationType.INVITE_RECEIVED,
            session=session,
        )
        await session.commit()
        return True

    async def accept_or_reject_invitation(
        self,
        user_uid: uuid.UUID,
        recipient_uid: uuid.UUID,
        board_uid: uuid.UUID,
        rejected: bool,
        session: AsyncSession,
    ):
        statement = select(Invitation).where(
            Invitation.user_uid == user_uid,
            Invitation.recipient_uid == recipient_uid,
            Invitation.board_uid == board_uid,
        )

        result = await session.exec(statement)
        final_result = result.one_or_none()
        if not final_result:
            raise InvitationNotFound()

        match rejected:
            case True:
                await session.delete(final_result)
                await session.commit()
                return False
            case False:
                final_result.accepted = True
                new_board_user = BoardUser(
                    user_uid=recipient_uid,
                    board_uid=board_uid,
                    role=UserRole.MEMBER,
                )
                session.add(new_board_user)
                await session.delete(final_result)

                from src.board.service import BoardService

                board_service = BoardService()

                await board_service.send_notification(
                    user_uid=user_uid,
                    board_uid=board_uid,
                    message_type=NotificationType.INVITE_ACCEPTED,
                    session=session,
                )

                await session.commit()
                return True

    async def get_user_info(self, user_uid: uuid.UUID, session: AsyncSession):
        statement = select(User).where(User.uid == user_uid)
        result = await session.exec(statement)
        result_first = result.first()
        if not result_first:
            raise UserNotFound()
        return result_first

    async def send_verify_account_email(self, user_email: str):

        token = create_url_safe_token({"email": user_email})

        link_verify = f"http://{Config.DOMAIN}/api/v1/users/verify/{token}"

        html_message = f"""
        <h1> Verify your account ! </h1>
        <p> Please click this <a href="{link_verify}">link</a> to verify your account </p>
        """

        emails = [user_email]
        subject = "Account verification"

        send_email.delay(emails, subject=subject, body=html_message)

        return True
