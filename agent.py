"""
agent.py - Simple AI Agent from scratch using Google Gemini.

Architecture:
  User Query
      |
      v
  [Agent Brain (Gemini)] <------+
      |                         |
      +---> [Function Call?]    |
      |          | Yes          |
      |          v              |
      |     [Tool Execution] ---+ (Feed results back to Gemini)
      |          |
      |          v No
      +---> [Final Answer]
"""

import os
import sys
import re
from typing import Any, Callable, List, Optional
from google import genai
from google.genai import types
from tools import TOOL_REGISTRY, TOOLS_LIST

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class SimpleAgent:
    """
    A lightweight, transparent AI agent built in pure Python.
    Implements the ReAct (Reasoning + Acting) loop with function calling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-flash-lite-latest",
        verbose: bool = True,
        mock: bool = False,
        extra_tools: Optional[dict[str, Callable[..., str]]] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.verbose = verbose
        self.mock = mock
        self.history: List[types.Content] = []
        self.tool_registry: dict[str, Callable[..., str]] = {
            **TOOL_REGISTRY,
            **(extra_tools or {}),
        }
        self.tools_list: list[Any] = list(self.tool_registry.values())

        self.system_instruction = (
            "You are an intelligent, proactive AI agent equipped with external tools.\n"
            "Tools available to you:\n"
            "- calculate(expression): For any arithmetic or math calculation.\n"
            "- get_current_time(timezone_name): For current date, time, and day.\n"
            "- search_wikipedia(query): For encyclopedia overviews of topics, people, and concepts.\n"
            "- search_web(query): For quick web queries, instant answers, and facts.\n"
            "- save_note(title, content): To save persistent notes to disk.\n"
            "- read_note(title): To read a previously saved note.\n"
            "- list_notes(): To see all saved notes.\n\n"
            "Google account tools are available only after the user connects Google:\n"
            "- search_gmail(query): Search Gmail read-only.\n"
            "- list_calendar_events(days): List upcoming Calendar events read-only.\n"
            "- create_calendar_event(title, start_iso, end_iso, confirmed): Create an event "
            "only when the user has explicitly confirmed it.\n\n"
            "Guidelines:\n"
            "1. Whenever a question requires current information, calculations, or saving notes, "
            "call the appropriate tool.\n"
            "2. You can call multiple tools across multiple steps if necessary.\n"
            "3. Once you have sufficient information from the tool results, formulate a concise, "
            "helpful, and well-structured final answer to the user."
        )
        if extra_tools:
            self.system_instruction += (
                "\n\nGoogle account status: CONNECTED. You have live access to the "
                "following Google tools. Use them instead of claiming the account is "
                "disconnected:\n"
                "- search_gmail(query): Search the user's Gmail messages.\n"
                "- list_calendar_events(days): Read the user's upcoming Calendar events.\n"
                "- create_calendar_event(title, start_iso, end_iso, confirmed): Create a "
                "Calendar event only after explicit user confirmation.\n"
                "If the user asks about an existing event, call list_calendar_events. "
                "If the user asks to create an event, gather the title, date, and times, "
                "then ask for confirmation before setting confirmed=true."
            )
        else:
            self.system_instruction += (
                "\n\nGoogle account status: NOT CONNECTED. Gmail and Calendar tools are "
                "unavailable in this session."
            )

        if not self.mock:
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. Please provide it or pass mock=True for offline demo."
                )
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def reset(self):
        """Resets the agent's conversation history."""
        self.history = []

    def _mock_think_and_act(self, user_input: str) -> str:
        """
        An offline mock agent loop that simulates how an LLM decides
        to call tools and synthesize answers without requiring an active API key.
        """
        lower = user_input.lower()

        # Math detection
        if any(w in lower for w in ["calculate", "math", "+", "-", "*", "/", "sqrt", "power"]):
            expr = user_input
            for phrase in ["can you please calculate", "can you calculate", "please calculate", "calculate", "what is", "evaluate"]:
                expr = re.sub(phrase, "", expr, flags=re.IGNORECASE)
            expr = expr.strip(" ?.:;")
            if not expr:
                expr = "25 * 14 + sqrt(144)"
            if self.verbose:
                print(f"  [Agent Thought] User is asking for math calculation. Calling 'calculate'.")
                print(f"  --> [Tool Call] calculate(expression='{expr}')")
            res = TOOL_REGISTRY["calculate"](expression=expr)
            if self.verbose:
                print(f"  <-- [Tool Output] {res}")
            return f"[Offline Demo Result] Calculated: {expr} = {res}"

        # Time detection
        if any(w in lower for w in ["time", "date", "today", "day"]):
            if self.verbose:
                print(f"  [Agent Thought] User is asking for current time. Calling 'get_current_time'.")
                print(f"  --> [Tool Call] get_current_time()")
            res = TOOL_REGISTRY["get_current_time"]()
            if self.verbose:
                print(f"  <-- [Tool Output] {res}")
            return f"[Offline Demo Result] {res}"

        # Note saving
        if "save note" in lower or "remember" in lower:
            title = "quick_note"
            content = user_input
            if self.verbose:
                print(f"  [Agent Thought] User wants to save a note. Calling 'save_note'.")
                print(f"  --> [Tool Call] save_note(title='{title}', content='...')")
            res = TOOL_REGISTRY["save_note"](title=title, content=content)
            if self.verbose:
                print(f"  <-- [Tool Output] {res}")
            return f"[Offline Demo Result] {res}"

        # Wikipedia / Search
        if any(w in lower for w in ["who is", "what is", "search", "wikipedia"]):
            query = user_input.replace("who is", "").replace("what is", "").replace("search", "").strip(" ?.")
            if not query:
                query = "Artificial Intelligence"
            if self.verbose:
                print(f"  [Agent Thought] User wants knowledge lookup for '{query}'. Calling 'search_wikipedia'.")
                print(f"  --> [Tool Call] search_wikipedia(query='{query}')")
            res = TOOL_REGISTRY["search_wikipedia"](query=query)
            if self.verbose:
                print(f"  <-- [Tool Output] {res[:120]}...")
            return f"[Offline Demo Result]\n{res}"

        return (
            "[Offline Demo Result] I am running in offline mock mode. "
            "Set your GEMINI_API_KEY in .env to unleash full Gemini reasoning!"
        )

    def run(self, user_input: str, max_steps: int = 6) -> str:
        """
        Executes the ReAct loop:
        1. Appends the user's message to conversation history.
        2. Queries Gemini with available tools.
        3. If Gemini asks to call tool(s), executes them locally and appends outputs.
        4. Repeats until Gemini generates a final text response or max_steps is reached.
        """
        if self.mock:
            return self._mock_think_and_act(user_input)

        # 1. Add user turn to conversation history
        self.history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_input)],
            )
        )

        step = 0
        while step < max_steps:
            step += 1
            if self.verbose:
                print(f"\n[Agent] Step {step}: Reasoning with Gemini ({self.model})...")

            # 2. Call Gemini model with manual tool calling control
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.history,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=self.tools_list,
                    temperature=0.2,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )

            # Record model turn in conversation history
            if response.candidates and response.candidates[0].content:
                self.history.append(response.candidates[0].content)

            # 3. Check if Gemini requested one or more tool calls
            if response.function_calls:
                tool_response_parts = []

                for call in response.function_calls:
                    func_name = call.name
                    args = call.args or {}

                    if self.verbose:
                        print(f"  [Tool Request] -> {func_name}({args})")

                    # Execute the tool function safely
                    if func_name in self.tool_registry:
                        try:
                            tool_result = self.tool_registry[func_name](**args)
                        except Exception as e:
                            tool_result = f"Error executing {func_name}: {str(e)}"
                    else:
                        tool_result = f"Error: Tool '{func_name}' is not registered."

                    if self.verbose:
                        preview = str(tool_result)[:160] + ("..." if len(str(tool_result)) > 160 else "")
                        print(f"  [Tool Output]  <- {preview}")

                    # Package tool response back for Gemini
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=func_name,
                            response={"result": str(tool_result)},
                        )
                    )

                # Feed tool results back into the conversation history
                self.history.append(types.Content(role="user", parts=tool_response_parts))
                # Loop continues so Gemini can inspect results and decide the next action
            else:
                # 4. Final response generated
                return response.text or "(No textual response generated)"

        return "Agent reached maximum step limit without arriving at a final response."
