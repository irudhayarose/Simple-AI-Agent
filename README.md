# 🤖 Simple AI Agent from Scratch

A lightweight, fully transparent AI Agent built with **pure Python** and the official **Google Gemini GenAI SDK (`google-genai`)**.

No heavy frameworks (no LangChain, no CrewAI, no AutoGen). Just pure, readable code demonstrating how modern AI agents actually work.

---

## 💡 What is an AI Agent?

An LLM alone is just a static predictor of text. An **AI Agent** turns an LLM into an autonomous system by combining three core pillars:

$$\text{Agent} = \text{Brain (LLM)} + \text{Hands (Tools)} + \text{Loop (ReAct / Decision Cycle)}$$

1. **The Brain (LLM)**: Analyzes user prompts and decides *if* and *which* tools to call.
2. **The Hands (Tools)**: Standard Python functions that interact with the outside world (math, APIs, files, databases).
3. **The Loop (ReAct: Reason + Act)**:
   - Gemini chooses a tool and provides parameters.
   - The agent executes the Python function locally.
   - The result is fed back to Gemini.
   - Gemini inspects the outcome and either takes another action or returns the final answer.

```
       User Request
            │
            ▼
┌───────────────────────┐
│ Gemini 2.5 Flash      │◄────────────────────────┐
│ (Reasoning Engine)    │                         │
└───────────┬───────────┘                         │
            │                                     │
    Requires a tool?                              │
       /         \                                │
    Yes           No                              │
     │             │                              │
     ▼             ▼                              │
┌───────────┐ ┌──────────────┐                    │
│ Execute   │ │ Final Answer │                    │
│ Python    │ │  to User     │                    │
│ Tool      │ └──────────────┘                    │
└─────┬─────┘                                     │
      │                                           │
      └────── Feeds Tool Result Back ─────────────┘
```

---

## 📁 Project Structure

```
simple_ai_agent/
├── agent.py         # The core SimpleAgent class & ReAct execution loop
├── tools.py         # Standard Python tool functions & tool registry
├── main.py          # Interactive command-line chat interface
├── app.py           # Streamlit web chat interface
├── notes/            # Storage directory for notes created by the agent
├── requirements.txt  # Python dependencies
├── google_services.py # Google OAuth, Gmail, and Calendar tools
├── secure_storage.py # Encrypted MongoDB and OS-keyring storage
├── .env.example     # Environment variable template
└── README.md        # Documentation and walkthrough
```

---

## 🛠️ Built-in Tools

| Tool | Purpose |
| :--- | :--- |
| `calculate` | Safely evaluates math expressions (`sqrt`, powers, arithmetic). |
| `get_current_time` | Checks the real-time date, time, and day of the week. |
| `search_wikipedia` | Fetches encyclopedic summaries from Wikipedia. |
| `search_web` | Searches DuckDuckGo for instant factual lookup. |
| `save_note` | Saves a text note into the `notes/` folder. |
| `read_note` | Reads a saved note by title. |
| `list_notes` | Lists all saved notes. |

---

## 🚀 Quickstart

### 1. Requirements

Ensure you have Python 3.10+ installed. The required packages (`google-genai` and `python-dotenv`) are installed:

```bash
pip install google-genai python-dotenv
```

### 2. Configure Your API Key

1. Grab a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Set your key in `.env`:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   GEMINI_MODEL=gemini-flash-lite-latest
   ```

*(If you don't set a key, the CLI will prompt you to enter it or let you run in offline mock mode!)*

### 3. Run the Agent

**Interactive Live Mode (Powered by Gemini):**
```bash
python main.py
```

**Offline Demo Mode (Runs without an API key):**
```bash
python main.py --mock
```

**Streamlit Web UI:**
```bash
streamlit run app.py
```

The web UI reads `GEMINI_API_KEY` and `GEMINI_MODEL` from `.env`. Use the
sidebar to start a new conversation, open previous conversations, delete chat
history, run in offline mock mode, change the model, or clear the current
conversation. After Google OAuth is configured, chat history is encrypted
before being stored in local MongoDB. OAuth refresh tokens are stored in the
operating system keyring, not MongoDB or chat history.

### Secure Google and MongoDB setup

1. In Google Cloud Console, create a project, enable Gmail API, Google Calendar
   API, and Google People API, then configure the OAuth consent screen.
2. Add the Gmail read-only and Calendar scopes requested by
   `google_services.py`.
3. Create an OAuth client of type **Desktop app**, download its JSON as
   `client_secret.json`, and keep it out of source control.
4. Install and start MongoDB locally.
5. Generate an encryption key:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
6. Set `CHAT_ENCRYPTION_KEY`, `MONGODB_URI`, and
   `GOOGLE_CLIENT_SECRET_FILE` in `.env`.
7. Run the UI:
   ```bash
   streamlit run app.py
   ```

Gmail access is read-only. Calendar creation is confirmation-gated: the agent
must receive `confirmed=true` only after the user explicitly confirms the
proposed event.

---

## 💬 Example Prompts to Try

- **Math & Multi-step reasoning:**
  > *"What is (145 * 12) + sqrt(14400)?"*
- **Real-time awareness:**
  > *"What date and time is it right now?"*
- **External knowledge lookup:**
  > *"Who was Ada Lovelace according to Wikipedia and what was her contribution?"*
- **File/Memory persistence:**
  > *"Save a note titled shopping_list with items: apples, coffee beans, and dark chocolate."*
  > *"What notes do I have saved?"*
  > *"Read my note titled shopping_list."*

---

## 🧩 How to Add Your Own Custom Tool

Adding a new tool to your agent takes only **3 simple steps**:

1. Open `tools.py`.
2. Define a Python function with **type hints** and a **clear docstring** (Gemini uses this docstring to know when to call it):

```python
def roll_dice(sides: int = 6) -> str:
    """Rolls a virtual die with a specified number of sides."""
    import random
    result = random.randint(1, sides)
    return f"Rolled a {sides}-sided die: {result}"
```

3. Add it to `TOOL_REGISTRY` at the bottom of `tools.py`:

```python
TOOL_REGISTRY = {
    # ... existing tools ...
    "roll_dice": roll_dice,
}
```

That's it! Gemini will automatically discover the tool and start using it whenever users ask to roll dice!
