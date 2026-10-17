"""Streamlit web interface for the Simple AI Agent."""

import os
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from agent import SimpleAgent
from google_services import (
    GoogleTools,
    authenticate_google,
    load_saved_google_session,
)
from secure_storage import SecureStorage
from secure_storage import delete_google_credentials


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

st.set_page_config(
    page_title="Simple AI Agent",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Simple AI Agent")
st.caption("Gemini-powered chat with calculation, web lookup, Wikipedia, and notes tools.")


def conversation_title(messages: list[dict]) -> str:
    first_user_message = next(
        (message["content"] for message in messages if message["role"] == "user"),
        "",
    )
    return first_user_message[:45] or "New conversation"


if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "agent_signature" not in st.session_state:
    st.session_state.agent_signature = None

if "google_tools" not in st.session_state:
    st.session_state.google_tools = None

if "google_user_id" not in st.session_state:
    st.session_state.google_user_id = None

if "storage_error" not in st.session_state:
    st.session_state.storage_error = None

if not st.session_state.google_user_id:
    try:
        saved_session = load_saved_google_session()
        if saved_session:
            st.session_state.google_user_id, credentials = saved_session
            st.session_state.google_tools = GoogleTools(credentials)
    except Exception as error:
        st.session_state.storage_error = f"Google session restore failed: {error}"


def get_storage() -> SecureStorage | None:
    if "storage" not in st.session_state:
        try:
            st.session_state.storage = SecureStorage()
        except (OSError, ValueError, RuntimeError) as error:
            st.session_state.storage_error = str(error)
            return None
    return st.session_state.storage


def load_user_conversations() -> list[dict]:
    if not st.session_state.google_user_id:
        return []
    storage = get_storage()
    if storage is None:
        return []
    try:
        return storage.load_conversations(st.session_state.google_user_id)
    except RuntimeError as error:
        st.session_state.storage_error = f"MongoDB is unavailable: {error}"
        return []


def persist_current_conversation() -> None:
    if not st.session_state.messages or not st.session_state.google_user_id:
        return
    conversation_id = st.session_state.conversation_id or str(uuid4())
    storage = get_storage()
    if storage is None:
        return
    storage.save_conversation(
        st.session_state.google_user_id,
        conversation_id,
        conversation_title(st.session_state.messages),
        st.session_state.messages,
    )
    st.session_state.conversation_id = conversation_id


def start_new_conversation() -> None:
    st.session_state.conversation_id = None
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.agent_signature = None


def select_conversation(conversation_id: str) -> None:
    conversation = next(item for item in load_user_conversations() if item["id"] == conversation_id)
    st.session_state.conversation_id = conversation_id
    st.session_state.messages = conversation["messages"]
    st.session_state.agent = None


with st.sidebar:
    st.header("Google account")
    if st.session_state.google_user_id:
        st.success(f"Connected: {st.session_state.google_user_id}")
        if st.button("Disconnect Google", use_container_width=True):
            delete_google_credentials(st.session_state.google_user_id)
            st.session_state.google_tools = None
            st.session_state.google_user_id = None
            start_new_conversation()
            st.rerun()

    if st.session_state.storage_error:
        st.warning(
            "Secure chat history is unavailable. Check CHAT_ENCRYPTION_KEY and "
            f"MongoDB: {st.session_state.storage_error}"
        )
    elif st.button("Connect Google account", use_container_width=True):
        try:
            with st.spinner("Complete Google sign-in in your browser..."):
                user_id, credentials = authenticate_google()
            st.session_state.google_user_id = user_id
            st.session_state.google_tools = GoogleTools(credentials)
            st.session_state.agent = None
            st.session_state.agent_signature = None
            st.rerun()
        except Exception as error:
            st.error(f"Google sign-in failed: {error}")

    st.header("Chat history")
    if st.button("＋ New conversation", use_container_width=True):
        start_new_conversation()
        st.rerun()

    conversations = load_user_conversations()
    if conversations:
        for conversation in conversations:
            label = conversation["title"]
            if st.button(
                label,
                key=f"conversation-{conversation['id']}",
                use_container_width=True,
            ):
                select_conversation(conversation["id"])
                st.rerun()
    else:
        st.caption("Your saved conversations will appear here.")

    if conversations:
        if st.button("Delete all history", use_container_width=True):
            storage = get_storage()
            if storage is not None:
                storage.delete_conversations(st.session_state.google_user_id)
            start_new_conversation()
            st.rerun()

    st.divider()
    st.header("Settings")
    mock_mode = st.toggle("Offline mock mode", value=False)
    model = st.text_input(
        "Gemini model",
        value=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        disabled=mock_mode,
    )

    if st.button("Clear conversation", use_container_width=True):
        start_new_conversation()
        st.rerun()

    st.divider()
    st.caption("Credentials stay in the OS keyring; chat content is encrypted in MongoDB.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask the agent something...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    persist_current_conversation()
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        extra_tools = {}
        if st.session_state.google_tools:
            extra_tools = {
                "search_gmail": st.session_state.google_tools.search_gmail,
                "list_calendar_events": st.session_state.google_tools.list_calendar_events,
                "create_calendar_event": st.session_state.google_tools.create_calendar_event,
            }
        agent_signature = (mock_mode, model, bool(st.session_state.google_tools))
        if (
            st.session_state.agent is None
            or st.session_state.agent_signature != agent_signature
        ):
            st.session_state.agent = SimpleAgent(
                api_key=os.getenv("GEMINI_API_KEY"),
                model=model,
                verbose=False,
                mock=mock_mode,
                extra_tools=extra_tools,
            )
            st.session_state.agent_signature = agent_signature

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.agent.run(prompt)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        persist_current_conversation()
    except Exception as error:
        message = f"Unable to process the request: {error}"
        with st.chat_message("assistant"):
            st.error(message)
        st.session_state.messages.append({"role": "assistant", "content": message})
        persist_current_conversation()
