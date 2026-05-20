# Board Management API

A fairly simple but quality REST API project covering essential production patterns, built with FastAPI. Features real-time notifications, role-based access control, email invitations, background job processing, and more.

# Personal notes

This project mainly covers all important FastAPI production patterns, but is still missing pytest testing, background job monitoring, redis caching and a few other things that i am going to add in the near future. This project is not really meant for production use, as it features an imaginary board system, but is a good skill practice.

---

## Features

- **Authentication** — jwt access and refresh tokens, email verification, token blocklist
- **Board Management** — create, update, archive, duplicate, and delete boards
- **Role-Based Access Control** — owner, admin, and member roles with permission enforcement
- **Invitations** — email based board invitations with accept/reject via tokenized links
- **Join Requests** — users can request to join public boards, admins approve or reject
- **Real-Time Notifications** — websocket powered instant notifications for all board events
- **Audit Logging** — full audit trail of every action on every board
- **Background Jobs** — email sending via Celery and Redis
- **Rate Limiting** — per user sliding window rate limiting on all endpoints
- **Search & Discovery** — full text search for boards and users + paginated public board listing
- **Pagination** — all list endpoints support page and size parameters

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL + SQLModel |
| Cache , Broker | Redis |
| Background Jobs | Celery |
| Real-Time | WebSockets |
| Auth | JWT |
| Email | FastAPI Mail |
| Migrations | Alembic |
| Logging | structlog |
| Config | pydantic-settings |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
src/
├── auth/
│   ├── dependencies.py     
│   ├── routes.py           
│   ├── schemas.py          
│   ├── service.py          
│   └── utils.py            
├── board/
│   ├── routes.py          
│   ├── schemas.py          
│   └── service.py          
├── db/
│   ├── main.py            
│   ├── models.py          
│   └── redis.py            
├── __init__.py            
├── celery_tasks.py        
├── config.py              
├── errors.py               
├── mail.py                 
├── middleware.py           
├── ratelimiter.py          
└── websocket_manager.py   
```

---

## Getting Started

### Basic requirements

- Python 3.11+
- PostgreSQL
- Redis

### Installation

```bash
git clone https://github.com/yourusername/board-management-api
cd board-management-api

python -m venv env
source env/bin/activate  # for mac & linux
env\Scripts\activate     # for windows

pip install -r requirements.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/task_manager
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
DOMAIN=localhost:8000
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
MAIL_FROM=your_email
MAIL_FROM_NAME=Board App
```

### Database Setup

```bash
alembic upgrade head
```

### Running Locally

```bash
fastapi dev src

celery -A src.celery_tasks worker --loglevel=info
```

### Running with Docker

```bash
docker compose up --build
```

---

## API Overview

### Auth / Users

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/users/create` | Register a new user | No |
| POST | `/api/v1/users/login` | Login and receive tokens | No |
| POST | `/api/v1/users/logout` | Revoke access token | Yes |
| GET | `/api/v1/users/verify/{token}` | Verify email address | No |
| GET | `/api/v1/users/me` | Get current user info | Yes |
| POST | `/api/v1/users/change_password` | Change password | Yes |
| GET | `/api/v1/users/get-user-boards` | Get all boards for current user | Yes |
| GET | `/api/v1/users/get-user-activity` | Get audit activity | Yes |
| GET | `/api/v1/users/get-user-invites` | Get pending invites | Yes |
| POST | `/api/v1/users/leave` | Leave a board | Yes |
| GET | `/api/v1/users/notifications` | Get notifications | Yes |
| POST | `/api/v1/users/notification-read` | Mark notification as read | Yes |
| POST | `/api/v1/users/notification-readall` | Mark all as read | Yes |
| POST | `/api/v1/users/request/board/{board_uid}` | Request to join public board | Yes |
| GET | `/api/v1/users/accept_invite/{token}` | Accept email invite | No |
| GET | `/api/v1/users/reject_invite/{token}` | Reject email invite | No |

### Board

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/board/create` | Create a board | Yes |
| GET | `/api/v1/board/details` | Get board details | Yes |
| POST | `/api/v1/board/update` | Update board | Yes |
| DELETE | `/api/v1/board/delete` | Delete board | Yes |
| POST | `/api/v1/board/archive` | Archive board | Yes |
| POST | `/api/v1/board/unarchive` | Unarchive board | Yes |
| POST | `/api/v1/board/duplicate` | Duplicate board | Yes |
| POST | `/api/v1/board/make-public` | Make board public | Yes |
| POST | `/api/v1/board/make-private` | Make board private | Yes |
| GET | `/api/v1/board/members` | List board members | Yes |
| POST | `/api/v1/board/member-update` | Update member role | Yes |
| POST | `/api/v1/board/member-remove` | Remove a member | Yes |
| GET | `/api/v1/board/audit` | View audit log | Yes |
| POST | `/api/v1/board/invite` | Send email invite | Yes |
| GET | `/api/v1/board/pending-requests` | View join requests | Yes |
| POST | `/api/v1/board/join-request-approve` | Approve join request | Yes |
| POST | `/api/v1/board/join-request-reject` | Reject join request | Yes |
| GET | `/api/v1/board/public` | List public boards | No |
| GET | `/api/v1/board/search` | Search boards | No |
| GET | `/api/v1/board/search-users` | Search users to invite | Yes |
| GET | `/api/v1/board/user-info` | Get member info | Yes |
| POST | `/api/v1/board/notify-user` | Send notification to member | Yes |
| POST | `/api/v1/board/notify-all-users` | Notify all members | Yes |

### WebSocket

| Endpoint | Description |
|---|---|
| `ws://host/api/v1/users/ws/{user_uid}` | Real-time notification stream |

---

## Notification System

Events that trigger real time WebSocket notifications:

| Event | Recipient |
|---|---|
| Invite sent | Target user |
| Invite accepted | Sender |
| Join request sent | Board owner |
| Join request approved | Requesting user |
| Join request rejected | Requesting user |
| Member removed | Removed user |
| Role changed | Affected user |
| Direct message | Target user or all members |

---

## Rate Limiting

All endpoints are rate limited per user with a Redis sliding window algorithm, with sensitive endpoints like login having 5 requests per 60 seconds, and so on
