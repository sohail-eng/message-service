# WhatsApp Message Gateway

Lightweight FastAPI microservice that registers applications with API keys and lets those apps send, retrieve, process, and delete WhatsApp messages. Designed as a simple queue layer that can later connect to a WhatsApp bot (WAHA, Baileys, etc.).

## Features

- Admin registration of applications (`X-Admin-Key`)
- Secure API keys (`wa_live_...`) stored as SHA-256 hashes only
- Application-scoped message send / list / delete / process
- SQLite + SQLAlchemy
- Health check endpoint

## Project structure

```
message-service/
├── main.py           # FastAPI app and routes
├── database.py       # Engine, session, Base
├── models.py         # SQLAlchemy models
├── schemas.py        # Pydantic schemas
├── auth.py           # Admin and app-key authentication
├── utils.py          # API key generation and hashing
├── requirements.txt
├── .env
└── whatsapp.db       # Created automatically on first run
```

## Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy or edit `.env`:

```env
ADMIN_SECRET_KEY=change-me-to-a-strong-secret
DATABASE_URL=sqlite:///./whatsapp.db
```

Set `ADMIN_SECRET_KEY` to a strong secret before using the service in any shared environment.

### 4. Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Or run with Docker

```bash
docker build -t message-service .
docker run --rm -p 8012:8012 \
  -e ADMIN_SECRET_KEY=change-me-to-a-strong-secret \
  -e DATABASE_URL=sqlite:///./whatsapp.db \
  message-service
```

Service: [http://127.0.0.1:8012](http://127.0.0.1:8012) · Docs: [http://127.0.0.1:8012/docs](http://127.0.0.1:8012/docs)

## API examples (curl)

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### Register an application (admin)

```bash
curl -X POST http://127.0.0.1:8000/admin/apps/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: change-me-to-a-strong-secret" \
  -d '{"app_name": "CRM System"}'
```

Example response:

```json
{
  "app_name": "CRM System",
  "app_key": "wa_live_xxxxx"
}
```

Save `app_key` — it is returned only once.

### List applications (admin)

```bash
curl http://127.0.0.1:8000/admin/apps \
  -H "X-Admin-Key: change-me-to-a-strong-secret"
```

### Delete an application (admin)

Permanently removes the application and its messages.

```bash
curl -X DELETE http://127.0.0.1:8000/admin/apps/1 \
  -H "X-Admin-Key: change-me-to-a-strong-secret"
```

### Send a message

```bash
curl -X POST http://127.0.0.1:8000/messages/send \
  -H "Content-Type: application/json" \
  -H "X-App-Key: wa_live_xxxxx" \
  -d '{"phone_number": "+923001234567", "message": "Hello customer"}'
```

### Retrieve pending messages (admin)

```bash
curl http://127.0.0.1:8000/messages \
  -H "X-Admin-Key: change-me-to-a-strong-secret"
```

### Mark a message as processed (admin)

```bash
curl -X POST http://127.0.0.1:8000/messages/1/process \
  -H "X-Admin-Key: change-me-to-a-strong-secret"
```

### Delete a message

```bash
curl -X DELETE http://127.0.0.1:8000/messages/1 \
  -H "X-App-Key: wa_live_xxxxx"
```

## Authentication

| Header        | Used by                                              |
|---------------|------------------------------------------------------|
| `X-Admin-Key` | `/admin/*`, `GET /messages`, `POST /messages/{id}/process` |
| `X-App-Key`   | `POST /messages/send`, `DELETE /messages/{id}`       |

## Message statuses

| Status      | Meaning                                      |
|-------------|----------------------------------------------|
| `pending`   | Queued, returned by `GET /messages`          |
| `processed` | Marked done via `POST /messages/{id}/process` |

## Notes

- Only the hashed API key is stored; the plaintext key is shown once at registration.
- Deleting an application hard-deletes it and cascades to its messages.
- Inactive applications cannot send messages.
- `GET /messages` returns all **pending** messages across apps (admin).
