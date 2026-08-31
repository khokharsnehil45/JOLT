#!/usr/bin/env python3
"""
SNIP - Natural Language to Terminal Command Agent
Theme: Clean Minimalist Monochrome & Cyan Accents
Features:
- Translates natural language requests into exact bash/zsh commands
- Explains flags and arguments clearly
- Safety level warnings (Safe, Caution, High Risk)
- One-key execution with confirmation
- Integrates with JOLT's existing Ollama and Cloud LLM configuration
"""

import sys
import os
import json
import re
import subprocess
import requests
import questionary
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich import box

console = Console()

BANNER_ART = r"""
  ___ _ __  _ _ __  
 / __| '_ \| | '_ \ 
 \__ \ | | | | |_) |
 |___/_| |_|_| .__/ 
             |_|    
"""

CONFIG_FILE = os.path.expanduser("~/.config/jolt/config.json")
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Clean Minimalist Styling (Cool Grey, Soft Blue, Clean Cyan)
MINIMAL_STYLE = Style([
    ('qmark', 'fg:#5fd7ff bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#5fd7ff bold'),
    ('pointer', 'fg:#5fd7ff bold'),
    ('highlighted', 'fg:#5fd7ff bold'),
    ('selected', 'fg:#87d7ff'),
    ('separator', 'fg:#444444'),
    ('instruction', 'fg:#666666'),
])

DEFAULT_CONFIG = {
    "provider": "groq",
    "model": "openai/gpt-oss-120b",
    "api_keys": {}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def print_header(model_info: str):
    header_text = Text()
    for line in BANNER_ART.strip().split("\n"):
        header_text.append(line + "\n", style="bold cyan")
    header_text.append("Natural Language Terminal Command Assistant\n", style="dim white")
    
    panel = Panel(
        header_text,
        box=box.SIMPLE,
        border_style="cyan",
        subtitle=f"[dim]Engine: {model_info}[/]",
        subtitle_align="right"
    )
    console.print(panel)

def parse_json_safely(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse valid JSON from output:\n{raw}")

def query_llm(prompt: str, system_prompt: str, cfg: dict) -> dict:
    provider = cfg.get("provider", "groq")
    model = cfg.get("model", "openai/gpt-oss-120b")
    keys = cfg.get("api_keys", {})

    if provider == "ollama":
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0}
        }
        resp = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama error: {resp.text}")
        return parse_json_safely(resp.json().get("response", ""))

    else:
        # OpenAI compatible (Groq, OpenAI, OpenRouter)
        if provider == "groq":
            endpoint = "https://api.groq.com/openai/v1/chat/completions"
            api_key = keys.get("groq") or os.getenv("GROQ_API_KEY")
        elif provider == "openai":
            endpoint = "https://api.openai.com/v1/chat/completions"
            api_key = keys.get("openai") or os.getenv("OPENAI_API_KEY")
        else:
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            api_key = keys.get("openrouter") or os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            raise ValueError(f"API key for {provider.upper()} is missing. Configure it via `jolt` or set environment variable.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0
        }
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"API error ({resp.status_code}): {resp.text}")
        content = resp.json()["choices"][0]["message"]["content"]
        return parse_json_safely(content)

def generate_terminal_command(user_query: str, cfg: dict) -> dict:
    os_info = f"{sys.platform} (Linux/Unix)"
    current_cwd = os.getcwd()
    
    system_prompt = f"""You are SNIP, an expert Linux/Unix terminal command generator.
The user's OS is: {os_info}. Current directory: {current_cwd}.

Translate the user's plain-English request into the single most optimal, secure bash command.

Safety Levels:
- "SAFE": Read-only, informational, or non-destructive (e.g. ls, find, grep, du, ps, curl).
- "CAUTION": Modifies files or restarts non-critical services (e.g. mv, cp, chmod, tar, docker restart).
- "HIGH_RISK": Destructive actions, recursive deletion, partition changes, system halt (e.g. rm -rf, dd, mkfs, kill -9 1).

Output format MUST be pure JSON with this exact structure:
{{
  "command": "the exact one-liner bash command",
  "explanation": "Brief 1-sentence summary of what this command accomplishes",
  "breakdown": [
    {{"part": "grep -rn", "description": "Recursively searches with line numbers"}},
    {{"part": "'TODO'", "description": "Search pattern"}}
  ],
  "safety_level": "SAFE" | "CAUTION" | "HIGH_RISK",
  "safety_warning": "Warning note if caution/high_risk, otherwise null"
}}"""

    return query_llm(f"User Request: {user_query}", system_prompt, cfg)

def display_command_card(result: dict):
    cmd = result.get("command", "").strip()
    explanation = result.get("explanation", "").strip()
    safety = result.get("safety_level", "SAFE").upper()
    warning = result.get("safety_warning")
    breakdown = result.get("breakdown", [])

    # Safety Tag Styling
    if safety == "HIGH_RISK":
        safety_badge = "[bold white on red] ⚠ HIGH RISK [/]"
        border_color = "red"
    elif safety == "CAUTION":
        safety_badge = "[bold black on yellow] ⚠ CAUTION [/]"
        border_color = "yellow"
    else:
        safety_badge = "[bold white on green] ✔ SAFE [/]"
        border_color = "cyan"

    # Command Box
    syntax = Syntax(cmd, "bash", theme="monokai", word_wrap=True)
    panel = Panel(
        syntax,
        title=f"[bold white]Suggested Command[/]  {safety_badge}",
        title_align="left",
        border_style=border_color,
        box=box.ROUNDED,
        subtitle=f"[dim]{explanation}[/]",
        subtitle_align="left"
    )
    console.print("\n")
    console.print(panel)

    # Explanation Table
    if breakdown:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim white", expand=True)
        table.add_column("Argument / Flag", style="bold cyan", ratio=2)
        table.add_column("Purpose", style="white", ratio=5)
        for item in breakdown:
            table.add_row(item.get("part", ""), item.get("description", ""))
        console.print(table)

    if warning:
        console.print(f"[bold yellow]Caution:[/] {warning}\n")

def execute_command(cmd: str):
    console.print(f"\n[dim cyan]─ Executing:[/] [bold white]{cmd}[/]\n")
    try:
        subprocess.run(cmd, shell=True, check=False)
    except Exception as e:
        console.print(f"[bold red]✖ Execution error:[/] {e}")
    console.print("\n[dim]─ Command execution finished.[/]\n")

def main():
    cfg = load_config()
    model_label = f"{cfg.get('provider', 'groq').upper()} ({cfg.get('model', 'openai/gpt-oss-120b')})"

    args = sys.argv[1:]
    
    # Direct argument invocation: `snip find all png files over 5mb`
    if args:
        user_query = " ".join(args)
        print_header(model_label)
        with console.status("[dim cyan]Generating command...[/]", spinner="dots"):
            try:
                result = generate_terminal_command(user_query, cfg)
            except Exception as e:
                console.print(f"[bold red]✖ Error:[/] {e}")
                sys.exit(1)

        display_command_card(result)
        
        cmd = result.get("command", "")
        if cmd:
            action = questionary.select(
                "Action:",
                choices=[
                    "▶ Run Command Now",
                    "📋 Copy Command to Clipboard",
                    "❌ Dismiss"
                ],
                style=MINIMAL_STYLE
            ).ask()

            if action and "Run Command" in action:
                execute_command(cmd)
            elif action and "Copy" in action:
                try:
                    import pyperclip
                    pyperclip.copy(cmd)
                    console.print("[bold green]✔ Copied to clipboard.[/]")
                except Exception:
                    # Fallback to xclip/wl-copy
                    os.system(f"echo -n '{cmd}' | xclip -selection clipboard 2>/dev/null || echo -n '{cmd}' | wl-copy 2>/dev/null")
                    console.print("[bold green]✔ Copied to clipboard.[/]")
        sys.exit(0)

    # Interactive Loop
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        print_header(model_label)
        
        user_query = questionary.text(
            "What would you like to do? (e.g. 'find all files modified in 24h'):",
            style=MINIMAL_STYLE
        ).ask()

        if not user_query or not user_query.strip():
            console.print("\n[dim]Goodbye.[/]\n")
            break

        with console.status("[dim cyan]Generating command...[/]", spinner="dots"):
            try:
                result = generate_terminal_command(user_query.strip(), cfg)
            except Exception as e:
                console.print(f"\n[bold red]✖ Error:[/] {e}\n")
                input("Press Enter to continue...")
                continue

        display_command_card(result)
        
        cmd = result.get("command", "")
        if cmd:
            action = questionary.select(
                "Action:",
                choices=[
                    "▶ Run Command Now",
                    "📋 Copy to Clipboard",
                    "🔄 Ask Another Command",
                    "❌ Exit"
                ],
                style=MINIMAL_STYLE
            ).ask()

            if action and "Run Command" in action:
                execute_command(cmd)
                input("Press Enter to continue...")
            elif action and "Copy" in action:
                os.system(f"echo -n '{cmd}' | xclip -selection clipboard 2>/dev/null || echo -n '{cmd}' | wl-copy 2>/dev/null")
                console.print("[bold green]✔ Copied to clipboard.[/]")
                time.sleep(1)
            elif action and "Exit" in action:
                break

if __name__ == "__main__":
    main()
