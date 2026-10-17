"""Encrypted local MongoDB storage and OS-keyring token storage."""

import json
import os
from datetime import datetime, timezone
from typing import Any

import keyring
from cryptography.fernet import Fernet
from pymongo import MongoClient

GOOGLE_KEYRING_SERVICE = "simple_ai_agent.google"
GOOGLE_ACTIVE_USER_KEY = "__active_user__"


class SecureStorage:
    def __init__(self) -> None:
        key = os.getenv("CHAT_ENCRYPTION_KEY", "").encode()
        if not key:
            raise ValueError("CHAT_ENCRYPTION_KEY is required for encrypted storage.")
        try:
            self.cipher = Fernet(key)
        except ValueError as error:
            raise ValueError("CHAT_ENCRYPTION_KEY is not a valid Fernet key.") from error

        self.client = MongoClient(
            os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=3000,
        )
        self.collection = self.client[
            os.getenv("MONGODB_DATABASE", "simple_ai_agent")
        ]["conversations"]
        self.collection.create_index([("user_id", 1), ("updated_at", -1)])

    def save_conversation(
        self, user_id: str, conversation_id: str, title: str, messages: list[dict[str, str]]
    ) -> None:
        payload = self.cipher.encrypt(json.dumps(messages).encode()).decode()
        self.collection.replace_one(
            {"user_id": user_id, "conversation_id": conversation_id},
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "title": title,
                "messages": payload,
                "updated_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )

    def load_conversations(self, user_id: str) -> list[dict[str, Any]]:
        conversations = []
        for item in self.collection.find({"user_id": user_id}).sort("updated_at", -1):
            messages = json.loads(self.cipher.decrypt(item["messages"].encode()))
            conversations.append(
                {
                    "id": item["conversation_id"],
                    "title": item["title"],
                    "updated_at": item["updated_at"].isoformat(),
                    "messages": messages,
                }
            )
        return conversations

    def delete_conversations(self, user_id: str) -> None:
        self.collection.delete_many({"user_id": user_id})


def save_google_credentials(user_id: str, credentials: Any) -> None:
    keyring.set_password(
        GOOGLE_KEYRING_SERVICE,
        user_id,
        credentials.to_json(),
    )
    keyring.set_password(GOOGLE_KEYRING_SERVICE, GOOGLE_ACTIVE_USER_KEY, user_id)


def load_google_credentials(user_id: str) -> str | None:
    return keyring.get_password(GOOGLE_KEYRING_SERVICE, user_id)


def load_active_google_user() -> str | None:
    return keyring.get_password(GOOGLE_KEYRING_SERVICE, GOOGLE_ACTIVE_USER_KEY)


def delete_google_credentials(user_id: str) -> None:
    try:
        keyring.delete_password(GOOGLE_KEYRING_SERVICE, user_id)
    except keyring.errors.PasswordDeleteError:
        pass
    try:
        keyring.delete_password(GOOGLE_KEYRING_SERVICE, GOOGLE_ACTIVE_USER_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
