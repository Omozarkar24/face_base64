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


@app.on_event("startup")
def startup() -> None:
    # No table creation needed — using existing urbn_users table
    pass


@app.get("/")
def health_check() -> dict:
    return {"status": "ok", "service": "Base64 Verification API"}


@app.get("/users/{user_id}")
def get_user(user_id: str) -> dict:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT usr_id, usr_name, usr_profile_image
                FROM urbn_users
                WHERE usr_id = %s AND usr_isactive = true AND usr_isdeleted = false
                """,
                (user_id,),
            )
            user_record = cursor.fetchone()

    if not user_record:
        return {
            "success": False,
            "message": "User not found",
        }

    return {
        "success": True,
        "usr_id": user_record["usr_id"],
        "usr_name": user_record["usr_name"],
        "has_profile_image": bool(user_record["usr_profile_image"]),
    }


@app.post("/fetch-data")
def fetch_data(payload: RequestPayload) -> dict:
    if not payload.base64_value or payload.base64_value.strip() == "":
        return {
            "code": 401,
            "success": False,
            "image_match": False,
            "message": "Image is missing or empty",
        }

    with get_connection() as connection:
        with connection.cursor() as cursor:
            # Look up user in urbn_users table
            cursor.execute(
                """
                SELECT usr_id, usr_name, usr_profile_image
                FROM urbn_users
                WHERE usr_id = %s AND usr_isactive = true AND usr_isdeleted = false
                """,
                (payload.user_id,),
            )
            user_record = cursor.fetchone()

            if not user_record:
                return {
                    "code": 404,
                    "success": False,
                    "image_match": False,
                    "message": "User not found in database",
                }

            stored_image = user_record["usr_profile_image"]

            # Check if user has a registered profile image
            if not stored_image or stored_image.strip() == "":
                return {
                    "code": 404,
                    "success": False,
                    "image_match": False,
                    "message": "No profile image registered for this user. Please upload profile image first.",
                }

            # Compare base64 images
            # Strip data URI prefix if present (e.g., "data:image/jpeg;base64,")
            sent_image = payload.base64_value.strip()
            db_image = stored_image.strip()

            # Remove data URI prefix from both if present
            if "," in sent_image:
                sent_image = sent_image.split(",", 1)[1]
            if "," in db_image:
                db_image = db_image.split(",", 1)[1]

            if sent_image != db_image:
                return {
                    "code": 401,
                    "success": False,
                    "image_match": False,
                    "message": "Face not matched",
                    "usr_id": payload.user_id,
                }

    return {
        "code": 200,
        "success": True,
        "image_match": True,
        "message": "Face matched successfully",
        "usr_id": payload.user_id,
        "usr_name": user_record["usr_name"],
    }
