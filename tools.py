"""
tools.py - Built-in tools for our Simple AI Agent.

Each tool is a standard Python function with type hints and a docstring.
The Gemini API automatically reads the function signature and docstring
to understand when and how to call the tool.
"""

import os
import ast
import math
import json
import datetime
import urllib.parse
import urllib.request
from typing import Dict, Any


def calculate(expression: str) -> str:
    """
    Evaluates a mathematical expression safely.
    Examples of valid expressions: '25 * 4', 'sqrt(144) + 10', '2 ** 8'.
    """
    try:
        # Allowed mathematical functions and constants
        allowed_names = {
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "pi": math.pi,
            "e": math.e,
            "pow": pow,
            "abs": abs,
            "round": round,
        }

        # Parse AST to ensure only safe mathematical expressions are evaluated
        node = ast.parse(expression, mode="eval")
        for subnode in ast.walk(node):
            if isinstance(subnode, (ast.Import, ast.ImportFrom, ast.Call)):
                # If it's a function call, ensure it's in allowed_names
                if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name):
                    if subnode.func.id not in allowed_names:
                        return f"Error: Function '{subnode.func.id}' is not allowed."
            if isinstance(subnode, ast.Name) and subnode.id not in allowed_names:
                return f"Error: Unknown symbol '{subnode.id}'."

        result = eval(compile(node, "<string>", "eval"), {"__builtins__": {}}, allowed_names)
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"


def get_current_time(timezone_name: str = "UTC") -> str:
    """
    Returns the current date, time, day of the week, and timezone.
    Optionally accepts a timezone name (e.g., 'UTC', 'local').
    """
    now = datetime.datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')}"


def search_wikipedia(query: str) -> str:
    """
    Searches Wikipedia for an encyclopedia summary of a topic, person, place, or concept.
    """
    try:
        encoded = urllib.parse.quote(query.strip().replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "SimpleAIAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            title = data.get("title", query)
            extract = data.get("extract", "")
            if extract:
                return f"Wikipedia ({title}):\n{extract}"
            return f"No summary found on Wikipedia for '{query}'."
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"No Wikipedia page found matching '{query}'."
        return f"Wikipedia request failed with status code {e.code}."
    except Exception as e:
        return f"Error querying Wikipedia: {str(e)}"


def search_web(query: str) -> str:
    """
    Searches DuckDuckGo for instant factual answers, definitions, and quick web lookups.
    """
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "SimpleAIAgent/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            abstract = data.get("AbstractText") or data.get("Abstract")
            if abstract:
                source = data.get("AbstractSource", "Web")
                url_src = data.get("AbstractURL", "")
                return f"DuckDuckGo Instant Answer ({source}):\n{abstract}\nSource: {url_src}"

            related = data.get("RelatedTopics", [])
            snippets = []
            for item in related[:3]:
                if isinstance(item, dict) and "Text" in item:
                    snippets.append(f"- {item['Text']}")

            if snippets:
                return "DuckDuckGo Related Results:\n" + "\n".join(snippets)

            return f"No direct summary found for '{query}'. Try search_wikipedia or another query."
    except Exception as e:
        return f"Web search error: {str(e)}"


NOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")


def save_note(title: str, content: str) -> str:
    """
    Saves a text note with a specific title to the agent's notes folder.
    Use this when the user asks to save, remember, or write down information.
    """
    try:
        os.makedirs(NOTES_DIR, exist_ok=True)
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe_title:
            safe_title = "untitled"
        filepath = os.path.join(NOTES_DIR, f"{safe_title}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved note '{safe_title}.txt' to notes directory."
    except Exception as e:
        return f"Failed to save note: {str(e)}"


def read_note(title: str) -> str:
    """
    Reads a saved note by its title from the notes folder.
    """
    try:
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        filepath = os.path.join(NOTES_DIR, f"{safe_title}.txt")
        if not os.path.exists(filepath):
            return f"Note '{safe_title}.txt' does not exist."
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Failed to read note: {str(e)}"


def list_notes() -> str:
    """
    Lists all saved notes in the agent's notes folder.
    """
    try:
        if not os.path.exists(NOTES_DIR):
            return "No notes directory found. No notes have been created yet."
        files = [f for f in os.listdir(NOTES_DIR) if f.endswith(".txt")]
        if not files:
            return "No notes saved yet."
        return "Saved notes:\n" + "\n".join(f"- {f}" for f in files)
    except Exception as e:
        return f"Failed to list notes: {str(e)}"


# Dictionary mapping tool names to python callable functions
TOOL_REGISTRY: Dict[str, Any] = {
    "calculate": calculate,
    "get_current_time": get_current_time,
    "search_wikipedia": search_wikipedia,
    "search_web": search_web,
    "save_note": save_note,
    "read_note": read_note,
    "list_notes": list_notes,
}

# List of tool functions to pass to Gemini
TOOLS_LIST = list(TOOL_REGISTRY.values())
