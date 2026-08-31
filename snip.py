#!/usr/bin/env python3
"""
SNIP - Natural Language to Terminal Command Agent
Theme: Clean Minimalist Monochrome & Cyan Accents
Features:
- Translates natural language requests into exact bash/zsh commands
- Explains flags and arguments clearly
- Safety level warnings (Safe, Caution, High Risk)
- One-key execution with confirmation
- Engine Switcher (Gemini, Groq, OpenAI, Claude, Local Ollama)
"""

import sys
import os
import json
import re
import time
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

# Clean Minimalist Styling
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
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "api_keys": {
        "gemini": "",
        "openai": "",
        "anthropic": "",
        "groq": "",
        "openrouter": ""
    }
}

CLOUD_PRESETS = {
    "gemini": [
        ("gemini-2.5-flash (Ultra Fast & Accurate)", "gemini-2.5-flash"),
        ("gemini-2.5-pro (Deep Reasoning)", "gemini-2.5-pro")
    ],
    "groq": [
        ("openai/gpt-oss-120b (High Performance)", "openai/gpt-oss-120b"),
        ("qwen/qwen3.8-27b (Fast Reasoning)", "qwen/qwen3.8-27b")
    ],
    "openai": [
        ("gpt-4o-mini (Fast)", "gpt-4o-mini"),
        ("gpt-4o (High Intelligence)", "gpt-4o")
    ],
    "anthropic": [
        ("claude-3-5-haiku-20241022", "claude-3-5-haiku-20241022"),
        ("claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20241022")
    ]
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

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

def call_gemini(api_key: str, model: str, prompt: str, system_prompt: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.0
        }
    }
    resp = requests.post(url, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    return parse_json_safely(content)

def call_openai_compatible(endpoint: str, api_key: str, model: str, prompt: str, system_prompt: str) -> dict:
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

def call_anthropic(api_key: str, model: str, prompt: str, system_prompt: str) -> dict:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": model,
        "system": system_prompt + "\nReturn ONLY a pure valid JSON object.",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
        "temperature": 0.0
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API error ({resp.status_code}): {resp.text}")
    content = resp.json()["content"][0]["text"].strip()
    return parse_json_safely(content)

def call_ollama(model: str, prompt: str, system_prompt: str) -> dict:
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

def query_llm(prompt: str, system_prompt: str, cfg: dict) -> dict:
    provider = cfg.get("provider", "gemini")
    model = cfg.get("model", "gemini-2.5-flash")
    keys = cfg.get("api_keys", {})

    if provider == "gemini":
        api_key = keys.get("gemini") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key missing. Configure it via `snip` settings or set GEMINI_API_KEY.")
        return call_gemini(api_key, model, prompt, system_prompt)

    elif provider == "groq":
        api_key = keys.get("groq") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key missing. Configure it via `snip` settings or set GROQ_API_KEY.")
        return call_openai_compatible("https://api.groq.com/openai/v1/chat/completions", api_key, model, prompt, system_prompt)

    elif provider == "openai":
        api_key = keys.get("openai") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key missing. Configure it via `snip` settings or set OPENAI_API_KEY.")
        return call_openai_compatible("https://api.openai.com/v1/chat/completions", api_key, model, prompt, system_prompt)

    elif provider == "anthropic":
        api_key = keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key missing. Configure it via `snip` settings or set ANTHROPIC_API_KEY.")
        return call_anthropic(api_key, model, prompt, system_prompt)

    elif provider == "ollama":
        return call_ollama(model, prompt, system_prompt)

    else:
        raise ValueError(f"Unknown provider '{provider}'")

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

    if safety == "HIGH_RISK":
        safety_badge = "[bold white on red] ⚠ HIGH RISK [/]"
        border_color = "red"
    elif safety == "CAUTION":
        safety_badge = "[bold black on yellow] ⚠ CAUTION [/]"
        border_color = "yellow"
    else:
        safety_badge = "[bold white on green] ✔ SAFE [/]"
        border_color = "cyan"

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

def switch_engine_menu(cfg: dict) -> dict:
    while True:
        curr_prov = cfg.get("provider", "gemini")
        curr_mod = cfg.get("model", "")
        
        console.print("\n[bold cyan]⚙ Select AI Engine for SNIP[/]")
        choice = questionary.select(
            f"Active: [{curr_prov.upper()}] - {curr_mod}",
            choices=[
                "🌐 Google Gemini (Gemini 2.5 Flash / Pro)",
                "⚡ Groq (Ultra-Fast Cloud LLMs)",
                "🌐 OpenAI (GPT-4o, GPT-4o-mini)",
                "🌐 Anthropic Claude (Claude 3.5 Sonnet / Haiku)",
                "🖥  Local Ollama (Offline Local LLMs)",
                "🔑 Configure API Keys",
                "↩ Back"
            ],
            style=MINIMAL_STYLE
        ).ask()

        if not choice or "Back" in choice:
            break

        if "Configure API Keys" in choice:
            keys = cfg.setdefault("api_keys", {})
            for prov in ["gemini", "groq", "openai", "anthropic"]:
                k = keys.get(prov, "")
                masked = (k[:4] + "..." + k[-4:]) if len(k) > 8 else ("(Set via ENV)" if os.getenv(f"{prov.upper()}_API_KEY") else "(Not Set)")
                console.print(f"[{prov.upper()}]: {masked}")
            
            p_to_edit = questionary.select("Select key to edit:", choices=["Gemini", "Groq", "OpenAI", "Anthropic", "Cancel"], style=MINIMAL_STYLE).ask()
            if p_to_edit and p_to_edit != "Cancel":
                new_key = questionary.password(f"Enter {p_to_edit.upper()} API Key:", style=MINIMAL_STYLE).ask()
                if new_key is not None:
                    keys[p_to_edit.lower()] = new_key.strip()
                    save_config(cfg)
                    console.print(f"[bold green]✔ Saved {p_to_edit.upper()} key.[/]")
                    time.sleep(1)

        elif "Local Ollama" in choice:
            cfg["provider"] = "ollama"
            cfg["model"] = "llama3.2:3b"
            save_config(cfg)
            console.print("[bold green]✔ Switched to Local Ollama.[/]")
            time.sleep(1)

        else:
            prov_key = "gemini" if "Gemini" in choice else "groq" if "Groq" in choice else "openai" if "OpenAI" in choice else "anthropic"
            
            key = cfg.get("api_keys", {}).get(prov_key, "") or os.getenv(f"{prov_key.upper()}_API_KEY", "")
            if not key:
                new_k = questionary.password(f"Enter {prov_key.upper()} API Key:", style=MINIMAL_STYLE).ask()
                if new_k:
                    cfg.setdefault("api_keys", {})[prov_key] = new_k.strip()
                    save_config(cfg)
                else:
                    continue

            presets = CLOUD_PRESETS.get(prov_key, [])
            sel_model = questionary.select(f"Select {prov_key.upper()} model:", choices=[l for l, _ in presets], style=MINIMAL_STYLE).ask()
            if sel_model:
                for l, m in presets:
                    if l == sel_model:
                        cfg["provider"] = prov_key
                        cfg["model"] = m
                        save_config(cfg)
                        console.print(f"[bold green]✔ Switched engine to {prov_key.upper()} ({m})[/]")
                        time.sleep(1)
                        break

    return cfg

def main():
    cfg = load_config()
    args = sys.argv[1:]
    
    if "--engine" in args or "engine" in args or "--config" in args:
        cfg = switch_engine_menu(cfg)
        sys.exit(0)

    model_label = f"{cfg.get('provider', 'gemini').upper()} ({cfg.get('model', 'gemini-2.5-flash')})"

    # Direct query argument: `snip find all png files over 5mb`
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
                os.system(f"echo -n '{cmd}' | xclip -selection clipboard 2>/dev/null || echo -n '{cmd}' | wl-copy 2>/dev/null")
                console.print("[bold green]✔ Copied to clipboard.[/]")
        sys.exit(0)

    # Interactive Loop
    while True:
        os.system('clear' if os.name != 'nt' else 'cls')
        model_label = f"{cfg.get('provider', 'gemini').upper()} ({cfg.get('model', 'gemini-2.5-flash')})"
        print_header(model_label)
        
        action = questionary.select(
            "Select action:",
            choices=[
                "💬 Ask a Terminal Command",
                "⚙ Switch AI Engine (Gemini, Groq, OpenAI, Claude, Ollama)",
                "❌ Exit"
            ],
            style=MINIMAL_STYLE
        ).ask()

        if not action or "Exit" in action:
            console.print("\n[dim]Goodbye.[/]\n")
            break

        if "Switch AI Engine" in action:
            cfg = switch_engine_menu(cfg)
            continue

        user_query = questionary.text(
            "What would you like to do? (e.g. 'find all files modified in 24h'):",
            style=MINIMAL_STYLE
        ).ask()

        if not user_query or not user_query.strip():
            continue

        with console.status("[dim cyan]Generating command with " + cfg.get("provider", "").upper() + "...[/]", spinner="dots"):
            try:
                result = generate_terminal_command(user_query.strip(), cfg)
            except Exception as e:
                console.print(f"\n[bold red]✖ Error:[/] {e}\n")
                input("Press Enter to continue...")
                continue

        display_command_card(result)
        
        cmd = result.get("command", "")
        if cmd:
            sub_action = questionary.select(
                "Action:",
                choices=[
                    "▶ Run Command Now",
                    "📋 Copy to Clipboard",
                    "🔄 Ask Another Command",
                    "❌ Exit"
                ],
                style=MINIMAL_STYLE
            ).ask()

            if sub_action and "Run Command" in sub_action:
                execute_command(cmd)
                input("Press Enter to continue...")
            elif sub_action and "Copy" in sub_action:
                os.system(f"echo -n '{cmd}' | xclip -selection clipboard 2>/dev/null || echo -n '{cmd}' | wl-copy 2>/dev/null")
                console.print("[bold green]✔ Copied to clipboard.[/]")
                time.sleep(1)
            elif sub_action and "Exit" in sub_action:
                break

if __name__ == "__main__":
    main()
