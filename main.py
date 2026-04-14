from datetime import datetime
import os

from dotenv import load_dotenv
from fastapi import FastAPI
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel

load_dotenv(".env")
load_dotenv(".env.example")

app = FastAPI(title="Base64 Verification API")

DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "prevoyance")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")


class RequestPayload(BaseModel):
    user_id: str
    base64_value: str


class UserUpsertPayload(BaseModel):
    user_id: str
    name: str
    langlong: str
    base64_value: str


def get_connection() -> psycopg.Connection:
    if DATABASE_URL:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        row_factory=dict_row,
    )


def init_db() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    langlong TEXT NOT NULL,
                    expected_base64 TEXT NOT NULL,
                    punching_time TEXT
                )
                """
            )
        connection.commit()


def seed_if_empty() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(1) AS total FROM users")
            existing_count = cursor.fetchone()["total"]
            if existing_count > 0:
                return

            sample_users = [
                (
                    "user_101",
                    "Alice",
                    "19.0760,72.8777",
                    "YWJjMTIz",
                    "2026-04-10 09:15:00",
                ),
                (
                    "user_202",
                    "Bob",
                    "28.6139,77.2090",
                    "c2VjcmV0NDU2",
                    "2026-04-10 10:05:00",
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO users (user_id, name, langlong, expected_base64, punching_time)
                VALUES (%s, %s, %s, %s, %s)
                """,
                sample_users,
            )
        connection.commit()


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_if_empty()


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "service": "Base64 Verification API"}


@app.post("/users/upsert")
def upsert_user(payload: UserUpsertPayload) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (user_id, name, langlong, expected_base64, punching_time)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    langlong = EXCLUDED.langlong,
                    expected_base64 = EXCLUDED.expected_base64,
                    punching_time = EXCLUDED.punching_time
                """,
                (payload.user_id, payload.name, payload.langlong, payload.base64_value, now),
            )
        connection.commit()

    return {
        "success": True,
        "message": "User record saved successfully",
        "UserID": payload.user_id,
    }


@app.get("/users/{user_id}")
def get_user(user_id: str) -> dict:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, name, langlong, expected_base64, punching_time
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )
            user_record = cursor.fetchone()

    if not user_record:
        return {
            "success": False,
            "message": "User ID not found in backend",
        }

    return {
        "success": True,
        "UserID": user_record["user_id"],
        "Name": user_record["name"],
        "Langlong": user_record["langlong"],
        "BASE 64": user_record["expected_base64"],
        "Punching time": user_record["punching_time"],
    }


@app.post("/fetch-data")
def fetch_data(payload: RequestPayload) -> dict:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, name, langlong, expected_base64, punching_time
                FROM users
                WHERE user_id = %s
                """,
                (payload.user_id,),
            )
            user_record = cursor.fetchone()

            if not user_record:
                return {
                    "code": 404,
                    "success": False,
                    "image_match": False,
                    "message": "User not found in backend",
                }

            if payload.base64_value != user_record["expected_base64"]:
                return {
                    "code": 401,
                    "success": False,
                    "image_match": False,
                    "message": "Image not matched (base64 does not match backend)",
                    "UserID": payload.user_id,
                }

            current_punching_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "UPDATE users SET punching_time = %s WHERE user_id = %s",
                (current_punching_time, payload.user_id),
            )
        connection.commit()

    return {
        "code": 200,
        "success": True,
        "image_match": True,
        "message": "Image matched successfully",
        "UserID": payload.user_id,
        "Name": user_record["name"],
        "Punching time": current_punching_time,
        "Langlong": user_record["langlong"],
        "BASE 64": payload.base64_value,
    }
