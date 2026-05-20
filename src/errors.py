from typing import Any, Callable
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request

class BoardException(Exception):
    pass

class InvalidToken(BoardException):
    pass

class RevokedToken(BoardException):
    pass

class AccesTokenRequired(BoardException):
    pass

class RefreshTokenRequired(BoardException):
    pass

class UserAlreadyExists(BoardException):
    pass

class InsufficientPermission(BoardException):
    pass

class BoardNotFound(BoardException):
    pass

class UserNotFound(BoardException):
    pass

class InvalidCredentials(BoardException):
    pass

class AccountNotVerified(BoardException):
    pass

class InvalidInput(BoardException):
    pass

class UserNotInBoard(BoardException):
    pass

class InvitationNotFound(BoardException):
    pass

class BoardUserNotFound(BoardException):
    pass

class NotificationNotFound(BoardException):
    pass

class RequestNotFound(BoardException):
    pass

def create_exception_handler(
        status_code: int, initial_detail: Any
) -> Callable[[Request,Exception], JSONResponse]:
    
    async def exception_handler(request: Request, exc: BoardException):
        return JSONResponse(content=initial_detail, status_code=status_code)
    
    return exception_handler

def register_all_errors(app: FastAPI):
    
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "User with email already exists",
                "error_code": "user_exists"
            }
        )
    )

    app.add_exception_handler(
        UserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "User was not found",
                "error_code": "user_not_found"
            }
        )
    )

    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Invalid email or password",
                "error_code": "invalid_credentials",
            },
        ),
    )

    app.add_exception_handler(
        InsufficientPermission,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "You don't have permission to perform this action",
                "error_code": "insufficient_permission",
            },
        ),
    )

    app.add_exception_handler(
        AccesTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Access token is required to perform this action",
                "error_code": "access_token_required",
            },
        ),
    )

    app.add_exception_handler(
        InvalidToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={"message": "Invalid token", "error_code": "invalid_token"},
        ),
    )

    app.add_exception_handler(
        RefreshTokenRequired,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Refresh token is required to perform this action",
                "error_code": "refresh_token_required",
            },
        ),
    )

    app.add_exception_handler(
        RevokedToken,
        create_exception_handler(
            status_code=status.HTTP_401_UNAUTHORIZED,
            initial_detail={
                "message": "Token has been revoked",
                "error_code": "revoked_token",
            },
        ),
    )

    app.add_exception_handler(
        BoardNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "Book with id not found",
                "error_code": "book_not_found",
            },
        ),
    )

    app.add_exception_handler(
        InvalidInput,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "The input provided by the user is invalid.",
                "error_code": "invalid_user_input",
            },
        ),
    )

    app.add_exception_handler(
        UserNotInBoard,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "The user is not in the specified board",
                "error_code": "user_not_in_board",
            },
        ),
    )

    app.add_exception_handler(
        InvitationNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "No valid invitation was found.",
                "error_code": "invitation_not_found",
            },
        ),
    )

    app.add_exception_handler(
        BoardUserNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "The board user was not found",
                "error_code": "board_user_not_found",
            },
        ),
    )

    app.add_exception_handler(
        NotificationNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "No valid notification was found",
                "error_code": "notification_not_found",
            },
        ),
    )

    app.add_exception_handler(
        RequestNotFound,
        create_exception_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            initial_detail={
                "message": "No valid request was found",
                "error_code": "request_not_found",
            },
        ),
    )

    @app.exception_handler(500)
    async def internal_server_error(request, exc):
        return JSONResponse(
            content={
                "message": "Oops! Something went wrong",
                "error_code": "server_error"
            },
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    



