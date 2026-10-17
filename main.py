"""
main.py - Interactive CLI for Simple AI Agent.

Run this script to chat with your AI agent:
    python main.py
Or in offline mock mode without an API key:
    python main.py --mock
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from agent import SimpleAgent
from tools import TOOL_REGISTRY

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file
load_dotenv()


def print_banner():
    print("=" * 65)
    print("           🤖 Welcome to Simple AI Agent from Scratch")
    print("=" * 65)
    print("Commands:")
    print("  - Type your request or question in natural language.")
    print("  - 'tools' : Show all available tools the agent can use.")
    print("  - 'clear' : Clear conversation memory.")
    print("  - 'exit'  : Quit the application.")
    print("=" * 65)


def print_tools():
    print("\n📦 Registered Agent Tools:")
    for name, func in TOOL_REGISTRY.items():
        doc = (func.__doc__ or "").strip().split("\n")[0]
        print(f"  • {name:<18} : {doc}")
    print()


def get_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        return api_key

    print("\n⚠️  No GEMINI_API_KEY found in your environment or .env file.")
    print("   You can get a free Gemini API key in 30 seconds at:")
    print("   👉 https://aistudio.google.com/app/apikey\n")

    choice = input("Paste your Gemini API key (or press Enter to run in offline Mock Mode): ").strip()
    if choice:
        # Save to .env for future convenience
        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nGEMINI_API_KEY={choice}\n")
        print("✅ Saved GEMINI_API_KEY to .env file.")
        return choice
    return ""


def main():
    parser = argparse.ArgumentParser(description="Simple AI Agent CLI")
    parser.add_argument("--mock", action="store_true", help="Run in offline mock mode without API key")
    parser.add_argument("--model", type=str, default=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"), help="Gemini model name")
    args = parser.parse_args()

    print_banner()

    api_key = "" if args.mock else get_api_key()
    is_mock = args.mock or (not api_key)

    if is_mock:
        print("\n🟡 Starting agent in [MOCK / DEMO MODE].")
        print("   (Tools will execute locally based on heuristics.)\n")
        agent = SimpleAgent(mock=True, verbose=True)
    else:
        print(f"\n🟢 Starting live agent powered by Gemini ({args.model}).\n")
        agent = SimpleAgent(api_key=api_key, model=args.model, verbose=True)

    while True:
        try:
            user_input = input("\nYou > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye! 👋")
                break

            if user_input.lower() == "clear":
                agent.reset()
                print("🧹 Conversation memory cleared.")
                continue

            if user_input.lower() == "tools":
                print_tools()
                continue

            # Run agent loop
            response = agent.run(user_input)

            print(f"\n🤖 Agent > {response}")

        except KeyboardInterrupt:
            print("\nSession interrupted. Exiting... 👋")
            break
        except Exception as e:
            print(f"\n❌ Error during execution: {e}")


if __name__ == "__main__":
    main()
