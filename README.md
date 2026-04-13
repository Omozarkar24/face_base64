# FastAPI Base64 Verification API (PostgreSQL)

## Install

```powershell
pip install -r requirements.txt
```

## PostgreSQL config

Set these environment variables (or put them in `.env`):

```env
DB_PORT=5432
DB_NAME=urbanattendance_db
DB_USER=postgres
DB_PASS=Pro@2023
DB_HOST=34.47.226.219
```

Optional fallback:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prevoyance
```

## Run

```powershell
python -m uvicorn main:app --reload
```

On startup, app auto-creates table `users` in PostgreSQL and seeds sample data if empty.

## Endpoints

- `POST /users/upsert` -> create or update backend user record
- `GET /users/{user_id}` -> view current backend record
- `POST /fetch-data` -> verify `user_id` + `base64_value`

## 1) Add or update backend user (Postman)

`POST /users/upsert`

```json
{
  "user_id": "user_202",
  "name": "Bob",
  "langlong": "28.6139,77.2090",
  "base64_value": "c2VjcmV0NDU2"
}
```

## 2) Verify from frontend/Postman

`POST /fetch-data`

```json
{
  "user_id": "user_202",
  "base64_value": "c2VjcmV0NDU2"
}
```

Match response:

```json
{
  "success": true,
  "image_match": true,
  "message": "Image matched successfully",
  "UserID": "user_202",
  "Name": "Bob",
  "Punching time": "2026-04-10 10:05:00",
  "Langlong": "28.6139,77.2090",
  "BASE 64": "c2VjcmV0NDU2"
}
```

Base64 mismatch response:

```json
{
  "success": false,
  "image_match": false,
  "message": "Image not matched (base64 does not match backend)",
  "UserID": "user_202"
}
```

User-not-found response:

```json
{
  "success": false,
  "image_match": false,
  "message": "User ID not found in backend"
}
```

## 3) Check backend user directly

`GET /users/user_202`
