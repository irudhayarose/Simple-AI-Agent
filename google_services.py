"""Google OAuth and least-privilege Gmail/Calendar tools."""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from secure_storage import (
    load_active_google_user,
    load_google_credentials,
    save_google_credentials,
)


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def load_saved_google_session() -> tuple[str, Credentials] | None:
    """Restore the last OAuth session from the OS keyring, refreshing if needed."""
    user_id = load_active_google_user()
    if not user_id:
        return None
    stored = load_google_credentials(user_id)
    if not stored:
        return None
    credentials = Credentials.from_authorized_user_info(json.loads(stored), SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_google_credentials(user_id, credentials)
    if not credentials.valid:
        return None
    return user_id, credentials


def authenticate_google() -> tuple[str, Credentials]:
    client_file = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
    if not os.path.exists(client_file):
        raise FileNotFoundError(
            f"Google OAuth client file not found: {client_file}"
        )

    saved_session = load_saved_google_session()
    credentials = saved_session[1] if saved_session else None

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
        credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    userinfo = build("oauth2", "v2", credentials=credentials).userinfo().get().execute()
    user_id = userinfo["email"]
    save_google_credentials(user_id, credentials)
    return user_id, credentials


class GoogleTools:
    def __init__(self, credentials: Credentials):
        self.gmail = build("gmail", "v1", credentials=credentials)
        self.calendar = build("calendar", "v3", credentials=credentials)

    def search_gmail(self, query: str, max_results: int = 10) -> str:
        """Searches Gmail messages using Gmail search syntax. Read-only."""
        result = self.gmail.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = []
        for item in result.get("messages", []):
            message = self.gmail.users().messages().get(
                userId="me", id=item["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()
            headers = {
                header["name"]: header["value"]
                for header in message.get("payload", {}).get("headers", [])
            }
            messages.append(
                f"Subject: {headers.get('Subject', '(no subject)')}\n"
                f"From: {headers.get('From', '')}\nDate: {headers.get('Date', '')}"
            )
        return "\n\n".join(messages) or "No matching messages found."

    def list_calendar_events(self, days: int = 7) -> str:
        """Lists upcoming Google Calendar events. Read-only."""
        now = datetime.now(timezone.utc)
        result = self.calendar.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=days)).isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        return "\n".join(
            f"{event.get('start', {}).get('dateTime', event.get('start', {}).get('date'))}: "
            f"{event.get('summary', '(untitled)')}"
            for event in events
        ) or "No upcoming events found."

    def create_calendar_event(
        self,
        title: str,
        start_iso: str,
        end_iso: str,
        confirmed: bool = False,
    ) -> str:
        """Creates an event only when confirmed is explicitly true by the user."""
        if not confirmed:
            return (
                "Confirmation required. Ask the user to explicitly confirm this "
                f"event: {title}, {start_iso} to {end_iso}."
            )
        event = self.calendar.events().insert(
            calendarId="primary",
            body={
                "summary": title,
                "start": {"dateTime": start_iso},
                "end": {"dateTime": end_iso},
            },
        ).execute()
        return f"Created calendar event: {event.get('htmlLink', event.get('id'))}"
