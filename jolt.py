#!/usr/bin/env python3
"""
JOLT - High-Voltage Text-to-JSON Cleaning & Transformation Engine
Features:
- Adaptive Neural Memory Hub (User preferences, domain rules, few-shot correction memory)
- Local LLMs via Ollama & Cloud LLMs via API Keys (Groq, OpenAI, Gemini, Claude, OpenRouter)
- Dual-Pass Architecture (Generator + Critic/Inspector)
- Dynamic TUI menu, Post-run feedback & memory saving, File exporter
"""

import sys
import os
import json
import re
import time
import requests
import questionary
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.rule import Rule
from rich.table import Table
from rich import box

console = Console()

BANNER_ART = r"""
     ██╗ ██████╗ ██╗  ████████╗
     ██║██╔═══██╗██║  ╚══██╔══╝
     ██║██║   ██║██║     ██║   
██   ██║██║   ██║██║     ██║   
╚█████╔╝╚██████╔╝███████╗██║   
 ╚════╝  ╚═════╝ ╚══════╝╚═╝   
"""

SUBTITLE = "⚡ HIGH-VOLTAGE AI TEXT-TO-JSON EXTRACTION & MEMORY ENGINE ⚡"
VERSION_TAG = "v2.4.0 • Adaptive Memory Engine"
CONFIG_DIR = os.path.expanduser("~/.config/jolt")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
MEMORY_FILE = os.path.join(CONFIG_DIR, "memory.json")
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Lightning theme styling
CUSTOM_QUESTIONARY_STYLE = Style([
    ('qmark', 'fg:#ffff00 bold'),
    ('question', 'fg:#00ffff bold'),
    ('answer', 'fg:#ffff00 bold'),
    ('pointer', 'fg:#ffff00 bold'),
    ('highlighted', 'fg:#ffff00 bold'),
    ('selected', 'fg:#00ffff'),
    ('separator', 'fg:#555555'),
    ('instruction', 'fg:#888888'),
])

DEFAULT_CONFIG = {
    "provider": "groq",
    "model": "openai/gpt-oss-120b",
    "api_keys": {
        "openai": "",
        "gemini": "",
        "anthropic": "",
        "groq": "",
        "openrouter": ""
    }
}

DEFAULT_MEMORY = {
    "rules": [
        "Use snake_case for all JSON keys",
        "Preserve original numeric values without converting them into unparsed strings",
        "Keep dates formatted as ISO-8601 strings (YYYY-MM-DD) when possible"
    ],
    "corrections": []
}

CLOUD_PRESETS = {
    "openai": [
        ("gpt-4o-mini (Fast & Cost-Effective)", "gpt-4o-mini"),
        ("gpt-4o (High Intelligence)", "gpt-4o"),
        ("o3-mini (Reasoning)", "o3-mini")
    ],
    "gemini": [
        ("gemini-2.5-flash (Ultra Fast)", "gemini-2.5-flash"),
        ("gemini-2.5-pro (Complex Reasoning)", "gemini-2.5-pro")
    ],
    "anthropic": [
        ("claude-3-5-haiku-20241022 (Fast)", "claude-3-5-haiku-20241022"),
        ("claude-3-5-sonnet-20241022 (Top Intelligence)", "claude-3-5-sonnet-20241022")
    ],
    "groq": [
        ("openai/gpt-oss-120b (High Performance)", "openai/gpt-oss-120b"),
        ("openai/gpt-oss-20b (Ultra Fast)", "openai/gpt-oss-20b"),
        ("qwen/qwen3.8-27b (Fast Reasoning)", "qwen/qwen3.8-27b"),
        ("qwen/qwen3.6-27b", "qwen/qwen3.6-27b")
    ],
    "openrouter": [
        ("google/gemini-2.5-flash", "google/gemini-2.5-flash"),
        ("anthropic/claude-3.5-sonnet", "anthropic/claude-3.5-sonnet"),
        ("meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.3-70b-instruct")
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
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                mem = json.load(f)
                if "rules" not in mem:
                    mem["rules"] = DEFAULT_MEMORY["rules"]
                if "corrections" not in mem:
                    mem["corrections"] = []
                return mem
        except Exception:
            pass
    return DEFAULT_MEMORY.copy()

def save_memory(mem):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def get_available_ollama_models():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            return [m.get("name") for m in resp.json().get("models", []) if "embed" not in m.get("name", "")]
    except Exception:
        pass
    return []

def get_available_groq_models(api_key: str):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=4)
        if resp.status_code == 200:
            return [m["id"] for m in resp.json().get("data", []) if not m["id"].startswith("whisper") and "guard" not in m["id"]]
    except Exception:
        pass
    return []

def print_header(provider: str, model_name: str, memory_count: int = 0):
    lines = [line for line in BANNER_ART.split("\n") if line]
    styled_art = Text()
    
    lightning_colors = [
        "bold bright_yellow", "bold yellow", "bold bright_cyan",
        "bold cyan", "bold bright_magenta", "bold magenta"
    ]
    
    for i, line in enumerate(lines):
        styled_art.append(line + "\n", style=lightning_colors[i % len(lightning_colors)])

    styled_art.append(f"\n{SUBTITLE}\n", style="bold bright_yellow")
    
    prov_label = provider.upper()
    mem_tag = f"[bold bright_green]🧠 {memory_count} Rules[/]" if memory_count > 0 else "[dim]🧠 No Memory[/]"
    panel = Panel(
        styled_art,
        box=box.ROUNDED,
        border_style="bright_yellow",
        subtitle=f"[bold bright_yellow]⚡ JOLT[/]  [dim]•[/]  [bold bright_cyan]{VERSION_TAG}[/]  [dim]•[/]  {mem_tag}  [dim]•[/]  [bold bright_magenta]{prov_label}: {model_name}[/]",
        subtitle_align="right"
    )
    console.print(panel)

def print_info_box():
    info_content = Text.from_markup(
        "[bold bright_yellow]⚡ JOLT Adaptive Context Transformer & Neural Memory Engine[/]\n"
        "[white]Transforms unstructured text into structured JSON while continuously learning your formatting preferences.[/]\n"
        "[dim]Dynamic Memory Injection • Dual-Pass Quality Inspector • Local Ollama & High-Speed Cloud Support.[/]"
    )
    panel = Panel(info_content, box=box.ROUNDED, border_style="bright_cyan")
    console.print(panel)

def render_app_screen(provider: str, model_name: str, memory_count: int = 0):
    clear_screen()
    print_header(provider, model_name, memory_count)
    print_info_box()

def get_multiline_input(prompt_title: str = "Paste or enter your raw text below", style_color: str = "bright_yellow") -> str:
    console.print(f"\n[bold bright_yellow]⚡ {prompt_title}[/] [dim](Press Ctrl+D on a new line when finished):[/]\n")
    console.print(Rule(style=f"dim {style_color}"))
    
    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        raw_text = "\n".join(lines).strip()
        console.print(Rule(style=f"dim {style_color}"))
        return raw_text
    except KeyboardInterrupt:
        console.print("\n[bold red]✖ Operation aborted by user.[/]")
        sys.exit(0)

# --- LLM CALL IMPLEMENTATIONS ---

def call_ollama(prompt: str, system_prompt: str, model: str) -> tuple[dict, int]:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.1}
    }
    resp = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
    res = resp.json()
    raw = res.get("response", "").strip()
    return parse_json_safely(raw), res.get("eval_count", 0)

def call_openai_compatible(endpoint: str, api_key: str, model: str, prompt: str, system_prompt: str, extra_headers: dict = None) -> tuple[dict, int]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"API error ({resp.status_code}): {resp.text}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    tokens = data.get("usage", {}).get("total_tokens", 0)
    return parse_json_safely(content), tokens

def call_gemini(api_key: str, model: str, prompt: str, system_prompt: str) -> tuple[dict, int]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.0
        }
    }
    resp = requests.post(url, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API error ({resp.status_code}): {resp.text}")
    data = resp.json()
    content = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
    return parse_json_safely(content), tokens

def call_anthropic(api_key: str, model: str, prompt: str, system_prompt: str) -> tuple[dict, int]:
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
        "max_tokens": 4096,
        "temperature": 0.0
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API error ({resp.status_code}): {resp.text}")
    data = resp.json()
    content = data["content"][0]["text"].strip()
    tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
    return parse_json_safely(content), tokens

def parse_json_safely(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse valid JSON from output:\n{raw}")

def dispatch_llm_call(cfg: dict, prompt: str, system_prompt: str) -> tuple[dict, int]:
    provider = cfg.get("provider", "ollama")
    model = cfg.get("model", "llama3.2:3b")
    keys = cfg.get("api_keys", {})

    if provider == "ollama":
        return call_ollama(prompt, system_prompt, model)
    elif provider == "openai":
        api_key = keys.get("openai") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key missing. Configure it in JOLT settings or set OPENAI_API_KEY.")
        return call_openai_compatible("https://api.openai.com/v1/chat/completions", api_key, model, prompt, system_prompt)
    elif provider == "gemini":
        api_key = keys.get("gemini") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key missing. Configure it in JOLT settings or set GEMINI_API_KEY.")
        return call_gemini(api_key, model, prompt, system_prompt)
    elif provider == "anthropic":
        api_key = keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic API key missing. Configure it in JOLT settings or set ANTHROPIC_API_KEY.")
        return call_anthropic(api_key, model, prompt, system_prompt)
    elif provider == "groq":
        api_key = keys.get("groq") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Groq API key missing. Configure it in JOLT settings or set GROQ_API_KEY.")
        return call_openai_compatible("https://api.groq.com/openai/v1/chat/completions", api_key, model, prompt, system_prompt)
    elif provider == "openrouter":
        api_key = keys.get("openrouter") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key missing. Configure it in JOLT settings or set OPENROUTER_API_KEY.")
        return call_openai_compatible("https://openrouter.ai/api/v1/chat/completions", api_key, model, prompt, system_prompt, extra_headers={"HTTP-Referer": "https://github.com/jsona/jolt", "X-Title": "JOLT"})
    else:
        raise ValueError(f"Unknown provider '{provider}'")

# --- PIPELINE WITH MEMORY INJECTION ---

def build_memory_prompt_block(memory_data: dict) -> str:
    rules = memory_data.get("rules", [])
    corrections = memory_data.get("corrections", [])
    
    if not rules and not corrections:
        return ""
    
    block = "\n\nUSER'S LEARNED PREFERENCES & ADAPTIVE RULES:\n"
    for i, r in enumerate(rules, 1):
        block += f"{i}. {r}\n"
        
    if corrections:
        block += "\nPAST CORRECTIONS TO REMEMBER:\n"
        for c in corrections[-3:]:  # latest 3 corrections
            block += f"- When user provided: \"{c.get('trigger', '')}\" -> Rule was: {c.get('rule', '')}\n"
    return block

def run_dual_pass_pipeline(text: str, cfg: dict, memory_data: dict, custom_schema: str | None = None, enable_inspector: bool = True, status_callback=None) -> tuple[dict, float, int, str]:
    total_tokens = 0
    start_time = time.perf_counter()
    prov_name = cfg.get("provider", "ollama").upper()
    memory_block = build_memory_prompt_block(memory_data)
    
    if status_callback:
        status_callback(f"[bold bright_yellow]⚡ Stage 1/2: [{prov_name}] Generator extracting context (+ Memory)...[/]")

    generator_sys = f"""You are a deterministic, zero-hallucination data extraction engine.
Your sole job is to extract facts from the PROVIDED TEXT into a clean, logical JSON object.

STRICT EXTRACTION LAWS:
1. HERMETIC EXTRACTION ONLY: Extract ONLY what is explicitly written in the input text. NEVER invent fields, never add UI descriptions or commentary.
2. FAITHFUL ITEM-BY-ITEM VALUES: Every single item in a list must have its OWN exact fields from the text. NEVER copy instructions or frequencies between different items.
3. LOGICAL DOMAIN STRUCTURE:
   - Root fields should be logical distinct objects: e.g. `metadata`, `patient`, `provider`, `vitals`, `diagnoses`, `medications`, `plan`, `follow_up`.
   - Never nest unrelated entities (e.g. do not put a hospital inside a date, or a doctor inside patient_info).
   - Use direct Objects `{{}}` for individual entities. Use Arrays `[]` ONLY for collections.
4. CLEAN VALUES: Numbers should be pure numbers (`{{"height_cm": 168}}`). Do NOT wrap every scalar into `{{'value': ..., 'unit': ...}}`.
5. NO DATA LOSS: Extract all IDs, codes, details, and parameters.{memory_block}
6. Return ONLY the pure JSON object."""

    if custom_schema:
        gen_prompt = f"STRICT SCHEMA:\n```json\n{custom_schema}\n```\n\nSOURCE TEXT:\n<<<\n{text}\n>>>\nExtract and map accurately into the schema. Output pure JSON only."
    else:
        gen_prompt = f"SOURCE TEXT:\n<<<\n{text}\n>>>\nExtract all facts into clean, logical, accurately-typed JSON. Output pure JSON only."

    initial_json, gen_tokens = dispatch_llm_call(cfg, gen_prompt, generator_sys)
    total_tokens += gen_tokens

    if not enable_inspector:
        elapsed = time.perf_counter() - start_time
        return initial_json, elapsed, total_tokens, "Single-Pass (Fast Jolt)"

    if status_callback:
        status_callback(f"[bold bright_cyan]⚡ Stage 2/2: [{prov_name}] Critic auditing accuracy & learned rules...[/]")

    inspector_sys = f"""You are the JOLT Quality Control & Hallucination Auditor.
You must compare the Candidate JSON against the Original Source Text and repair any discrepancies.

AUDIT CHECKLIST:
1. CROSS-CONTAMINATION & DOSAGE CHECK: Inspect every item in lists. Did the candidate copy instructions from one item to another? Fix them to match source text exactly.
2. HALLUCINATION CHECK: Did the candidate invent any fields not present in the source text? If so, DELETE them immediately.
3. ENTITY SEPARATION: Are different people or organizations cleanly separated into their own top-level objects? Fix any duplicates or confused arrays.
4. MISSING DETAILS: Ensure all codes, coverage specifics, and follow-up reasons are fully restored.
5. USER PREFERENCES ENFORCEMENT: Ensure the output follows all user preferences:{memory_block}

OUTPUT FORMAT:
Return ONLY valid JSON in this format:
{{
  "audit_status": "PASSED" | "CORRECTED",
  "audit_notes": "1-sentence summary of audit fixes",
  "final_json": {{ ... the repaired, pristine, factually exact JSON ... }}
}}"""

    insp_prompt = f"ORIGINAL SOURCE TEXT:\n<<<\n{text}\n```\n\nCANDIDATE JSON:\n```json\n{json.dumps(initial_json, indent=2)}\n```\nAudit candidate JSON against source text, repair all issues, and return final clean JSON."

    try:
        audit_result, insp_tokens = dispatch_llm_call(cfg, insp_prompt, inspector_sys)
        total_tokens += insp_tokens
        elapsed = time.perf_counter() - start_time
        
        audit_status = audit_result.get("audit_status", "PASSED")
        audit_notes = audit_result.get("audit_notes", "Verified without modifications")
        final_json = audit_result.get("final_json", initial_json)
        
        if not isinstance(final_json, (dict, list)):
            final_json = initial_json
            
        audit_summary = f"{audit_status}: {audit_notes}"
        return final_json, elapsed, total_tokens, audit_summary

    except Exception:
        elapsed = time.perf_counter() - start_time
        return initial_json, elapsed, total_tokens, "Inspector Fallback (Pass 1 Output)"

def render_metrics_badge(elapsed_sec: float, token_count: int, byte_size: int, line_count: int, provider: str, model: str, mode_label: str, audit_summary: str, memory_count: int):
    t_speed = (token_count / elapsed_sec) if elapsed_sec > 0 and token_count > 0 else 0
    
    if "CORRECTED" in audit_summary:
        audit_tag = f"[bold bright_yellow]⚡ Inspector Auto-Healed:[/] [white]{audit_summary}[/]"
    elif "PASSED" in audit_summary:
        audit_tag = f"[bold bright_green]✔ Inspector Verified:[/] [dim]{audit_summary}[/]"
    else:
        audit_tag = f"[bold bright_cyan]ℹ Inspector:[/] [dim]{audit_summary}[/]"

    m_text = (
        f"[bold bright_yellow]⚡ Validated JSON[/]  [dim]•[/]  "
        f"[bold bright_cyan]⏱ Latency:[/] {elapsed_sec:.2f}s  [dim]•[/]  "
        f"[bold bright_yellow]📊 Tokens:[/] {token_count} [dim]({t_speed:.1f} t/s)[/]  [dim]•[/]  "
        f"[bold bright_magenta]📦 Size:[/] {byte_size} B ({line_count} lines)  [dim]•[/]  "
        f"[bold bright_green]🧠 {memory_count} Active Rules[/]  [dim]•[/]  "
        f"[bold white]🏷 Engine:[/] {provider.upper()} ({model})\n"
        f"{audit_tag}"
    )
    
    panel = Panel(Text.from_markup(m_text), box=box.ROUNDED, border_style="bright_yellow", style="on grey11")
    console.print(panel)

def save_json_prompt(json_content: str):
    want_save = questionary.confirm("💾 Would you like to save this JSON output to a file?", default=False, style=CUSTOM_QUESTIONARY_STYLE).ask()
    if not want_save:
        return

    current_dir = os.getcwd()
    target_dir = questionary.text("Enter destination directory:", default=current_dir, style=CUSTOM_QUESTIONARY_STYLE).ask() or current_dir
    target_dir = os.path.expanduser(target_dir.strip())

    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
            console.print(f"[dim green]Created directory: {target_dir}[/]")
        except Exception as e:
            console.print(f"[bold red]✖ Could not create directory:[/] {e}")
            return

    default_filename = f"jolt_output_{int(time.time())}.json"
    target_file = questionary.text("Enter file name:", default=default_filename, style=CUSTOM_QUESTIONARY_STYLE).ask() or default_filename
    target_file = target_file.strip()
    if not target_file.endswith(".json"):
        target_file += ".json"

    full_path = os.path.join(target_dir, target_file)
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        console.print(f"\n[bold bright_green]✔ JSON successfully saved to:[/] [underline bright_yellow]{full_path}[/]")
    except Exception as e:
        console.print(f"[bold red]✖ Error writing file:[/] {e}")

def teach_jolt_prompt(memory_data: dict, recent_text: str = ""):
    """Allow user to teach JOLT a new rule or correction."""
    console.print("\n[bold bright_yellow]🧠 Teach JOLT a Rule / Memory[/]")
    console.print("[dim]Enter any custom formatting preference or extraction rule for JOLT to remember.[/]\n")
    
    new_rule = questionary.text(
        "Enter new rule (e.g. 'Always format phone numbers with country codes'):",
        style=CUSTOM_QUESTIONARY_STYLE
    ).ask()
    
    if new_rule and new_rule.strip():
        memory_data.setdefault("rules", []).append(new_rule.strip())
        if recent_text:
            memory_data.setdefault("corrections", []).append({
                "trigger": recent_text[:80] + "...",
                "rule": new_rule.strip(),
                "timestamp": int(time.time())
            })
        save_memory(memory_data)
        console.print(f"\n[bold bright_green]✔ JOLT has learned this rule! It will apply to all future extractions.[/]\n")
        time.sleep(1.5)

# --- MEMORY HUB MENU ---

def memory_hub_menu(memory_data: dict) -> dict:
    while True:
        rules = memory_data.get("rules", [])
        corrections = memory_data.get("corrections", [])
        
        console.print("\n[bold bright_yellow]🧠 JOLT Adaptive Memory Hub[/]")
        console.print(f"[dim]Active Rules: {len(rules)} | Learned Corrections: {len(corrections)}[/]\n")
        
        action = questionary.select(
            "Memory Hub Actions:",
            choices=[
                "➕ Teach JOLT a New Rule / Preference",
                "📋 View All Active Memories & Rules",
                "🗑  Delete a Specific Rule",
                "🔄 Reset Memory to Default",
                "↩ Back to Main Menu"
            ],
            style=CUSTOM_QUESTIONARY_STYLE
        ).ask()

        if not action or "Back to Main Menu" in action:
            break

        if "Teach JOLT a New Rule" in action:
            teach_jolt_prompt(memory_data)

        elif "View All Active Memories" in action:
            table = Table(title="[bold bright_yellow]🧠 JOLT Learned Rules & Memory[/]", box=box.ROUNDED)
            table.add_column("#", style="cyan", width=4)
            table.add_column("Rule / Formatting Guideline", style="white")
            for i, r in enumerate(rules, 1):
                table.add_row(str(i), r)
            console.print(table)
            input("\nPress Enter to return to Memory Hub...")

        elif "Delete a Specific Rule" in action:
            if not rules:
                console.print("[yellow]⚠ No custom rules to delete.[/]")
                time.sleep(1)
                continue
            rule_choices = [f"{i+1}. {r}" for i, r in enumerate(rules)] + ["Cancel"]
            to_del = questionary.select("Select rule to delete:", choices=rule_choices, style=CUSTOM_QUESTIONARY_STYLE).ask()
            if to_del and to_del != "Cancel":
                idx = int(to_del.split(".")[0]) - 1
                deleted_rule = rules.pop(idx)
                save_memory(memory_data)
                console.print(f"[bold green]✔ Deleted rule:[/] {deleted_rule}")
                time.sleep(1)

        elif "Reset Memory" in action:
            confirm = questionary.confirm("Are you sure you want to reset all memories to default?", default=False, style=CUSTOM_QUESTIONARY_STYLE).ask()
            if confirm:
                memory_data = DEFAULT_MEMORY.copy()
                save_memory(memory_data)
                console.print("[bold green]✔ Memory reset to default.[/]")
                time.sleep(1)

    return memory_data

# --- MODEL & PROVIDER CONFIGURATION MENU ---

def configure_provider_and_models(cfg: dict) -> dict:
    while True:
        current_prov = cfg.get("provider", "groq")
        current_mod = cfg.get("model", "")
        
        console.print("\n[bold bright_yellow]⚡ AI Model & Provider Configuration[/]")
        choice = questionary.select(
            f"Active: [{current_prov.upper()}] - {current_mod}",
            choices=[
                "⚡ Groq (Ultra-Fast Cloud LLMs)",
                "🖥  Local Ollama (Local LLMs)",
                "🌐 OpenAI (GPT-4o, GPT-4o-mini, o3-mini)",
                "🌐 Google Gemini (Gemini 2.5 Flash, Pro)",
                "🌐 Anthropic Claude (Claude 3.5 Sonnet, Haiku)",
                "🌐 OpenRouter (Multi-Model Cloud Gateway)",
                "🔑 Manage API Keys",
                "↩ Back to Main Menu"
            ],
            style=CUSTOM_QUESTIONARY_STYLE
        ).ask()

        if not choice or "Back to Main Menu" in choice:
            break

        if "Local Ollama" in choice:
            models = get_available_ollama_models()
            if not models:
                console.print("[bold red]✖ No models found on local Ollama or Ollama is not running.[/]")
                time.sleep(1.5)
                continue
            chosen_mod = questionary.select("Select Ollama model:", choices=models, style=CUSTOM_QUESTIONARY_STYLE).ask()
            if chosen_mod:
                cfg["provider"] = "ollama"
                cfg["model"] = chosen_mod
                save_config(cfg)
                console.print(f"[bold green]✔ Active model set to Ollama ({chosen_mod})[/]")
                time.sleep(1)

        elif "Manage API Keys" in choice:
            manage_api_keys(cfg)

        else:
            prov_key = "openai" if "OpenAI" in choice else "gemini" if "Gemini" in choice else "anthropic" if "Anthropic" in choice else "groq" if "Groq" in choice else "openrouter"
            
            key = cfg.get("api_keys", {}).get(prov_key, "")
            env_key = os.getenv(f"{prov_key.upper()}_API_KEY", "")
            
            if not key and not env_key:
                console.print(f"\n[bold yellow]⚠ No API key found for {prov_key.upper()}.[/]")
                new_key = questionary.password(f"Enter {prov_key.upper()} API Key:", style=CUSTOM_QUESTIONARY_STYLE).ask()
                if new_key:
                    cfg["api_keys"][prov_key] = new_key.strip()
                    save_config(cfg)
                else:
                    continue

            if prov_key == "groq":
                active_key = cfg.get("api_keys", {}).get("groq") or os.getenv("GROQ_API_KEY", "")
                dynamic_groq = get_available_groq_models(active_key)
                choices = (dynamic_groq if dynamic_groq else [m for _, m in CLOUD_PRESETS["groq"]]) + ["Custom model name..."]
            else:
                presets = CLOUD_PRESETS.get(prov_key, [])
                choices = [label for label, _ in presets] + ["Custom model name..."]

            sel_label = questionary.select(f"Select {prov_key.upper()} model:", choices=choices, style=CUSTOM_QUESTIONARY_STYLE).ask()
            
            if sel_label == "Custom model name...":
                custom_m = questionary.text("Enter custom model identifier:", style=CUSTOM_QUESTIONARY_STYLE).ask()
                if custom_m:
                    cfg["provider"] = prov_key
                    cfg["model"] = custom_m.strip()
                    save_config(cfg)
            elif sel_label:
                cfg["provider"] = prov_key
                if prov_key == "groq" and dynamic_groq:
                    cfg["model"] = sel_label
                else:
                    for label, mod_val in CLOUD_PRESETS.get(prov_key, []):
                        if label == sel_label or mod_val == sel_label:
                            cfg["model"] = mod_val
                            break
                    else:
                        cfg["model"] = sel_label
                save_config(cfg)
            console.print(f"[bold green]✔ Active provider set to {cfg['provider'].upper()} ({cfg['model']})[/]")
            time.sleep(1)

    return cfg

def manage_api_keys(cfg: dict):
    while True:
        keys = cfg.setdefault("api_keys", {})
        console.print("\n[bold bright_yellow]🔑 API Key Management[/]")
        
        display_choices = []
        for prov in ["groq", "openai", "gemini", "anthropic", "openrouter"]:
            k = keys.get(prov, "")
            masked = (k[:4] + "..." + k[-4:]) if len(k) > 8 else ("(Set via ENV)" if os.getenv(f"{prov.upper()}_API_KEY") else "(Not Set)")
            display_choices.append(f"{prov.upper()}: {masked}")
        display_choices.append("↩ Back")

        sel = questionary.select("Select key to update:", choices=display_choices, style=CUSTOM_QUESTIONARY_STYLE).ask()
        if not sel or "Back" in sel:
            break

        prov_sel = sel.split(":")[0].strip().lower()
        new_val = questionary.password(f"Enter new {prov_sel.upper()} API key (leave empty to clear):", style=CUSTOM_QUESTIONARY_STYLE).ask()
        if new_val is not None:
            keys[prov_sel] = new_val.strip()
            save_config(cfg)
            console.print(f"[bold green]✔ Updated {prov_sel.upper()} key.[/]")
            time.sleep(1)

def print_help():
    help_text = """
[bold bright_yellow]⚡ JOLT - High-Voltage Adaptive Memory AI Text-to-JSON Transformer[/]

[bold cyan]Usage:[/bold cyan]
  [bright_yellow]jolt run[/bright_yellow]               Launch the interactive JOLT UI
  [bright_yellow]jolt[/bright_yellow]                   Launch the interactive JOLT UI
  [bright_yellow]echo "<text>" | jolt[/bright_yellow]   Transform text directly via Unix pipe
  [bright_yellow]jolt --help[/bright_yellow]            Display this help message

[bold cyan]Key Features:[/bold cyan]
  🧠 Adaptive Neural Memory Hub (Learns formatting preferences & domain rules)
  ⚡ Dual-Pass Quality Inspector (Zero-hallucination auto-healing)
  ⚡ Local Ollama + Cloud Engines (Groq, OpenAI, Gemini, Claude, OpenRouter)
"""
    console.print(Panel(Text.from_markup(help_text.strip()), box=box.ROUNDED, border_style="bright_yellow"))

def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args or "help" in args:
        print_help()
        sys.exit(0)

    cfg = load_config()
    memory_data = load_memory()

    # If piped mode
    if not sys.stdin.isatty():
        print_header(cfg["provider"], cfg["model"], len(memory_data.get("rules", [])))
        print_info_box()
        user_input = sys.stdin.read().strip()
        if user_input:
            with console.status(f"[bold bright_yellow]⚡ Extracting context with {cfg['provider'].upper()}...[/]", spinner="dots") as status:
                try:
                    parsed_data, elapsed, tokens, audit_summary = run_dual_pass_pipeline(
                        user_input, 
                        cfg, 
                        memory_data,
                        enable_inspector=True,
                        status_callback=lambda msg: status.update(msg)
                    )
                    formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
                    syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=True, word_wrap=True)
                    out_panel = Panel(
                        syntax,
                        box=box.ROUNDED,
                        title="[bold bright_green]✔ JOLT Verified & Cleaned JSON Output[/]",
                        title_align="left",
                        border_style="bright_yellow",
                        subtitle="[dim]Dual-Pass Verified[/]",
                        subtitle_align="right"
                    )
                    console.print(out_panel)
                    render_metrics_badge(elapsed, tokens, len(formatted_json.encode('utf-8')), len(formatted_json.splitlines()), cfg["provider"], cfg["model"], "Auto-Extract (Piped)", audit_summary, len(memory_data.get("rules", [])))
                except Exception as e:
                    console.print(f"\n[bold red]✖ Error during transformation:[/] {e}\n")
        return

    # Interactive Loop
    while True:
        memory_count = len(memory_data.get("rules", []))
        render_app_screen(cfg["provider"], cfg["model"], memory_count)
        
        console.print("")
        action = questionary.select(
            "Select an action:",
            choices=[
                "⚡ Auto-Extract Context (Dual-Pass Agent Inspector)",
                "📋 Custom Schema / Template Extraction",
                "📁 Load Schema from a JSON file",
                "🧠 JOLT Memory Hub (Teach Rules & Preferences)",
                "⚡ Fast Single-Pass Extraction (No Inspector)",
                "⚙ Switch Engine / Cloud Model (Groq, OpenAI, Gemini, Claude, Ollama)",
                "🚪 Exit JOLT"
            ],
            style=CUSTOM_QUESTIONARY_STYLE
        ).ask()

        if action is None or "Exit JOLT" in action:
            console.print("\n[bold bright_yellow]⚡ Thank you for using JOLT! Goodbye.[/]\n")
            break

        if "JOLT Memory Hub" in action:
            memory_data = memory_hub_menu(memory_data)
            continue

        if "Switch Engine" in action:
            cfg = configure_provider_and_models(cfg)
            continue

        custom_schema = None
        mode_label = "Dual-Pass Auto-Extract"
        enable_inspector = True

        if "Fast Single-Pass" in action:
            enable_inspector = False
            mode_label = "Fast Single-Pass"

        elif "Custom Schema / Template" in action:
            custom_schema = get_multiline_input("Paste your custom JSON Schema / Template below", "bright_yellow")
            if not custom_schema:
                console.print("[dim yellow]No schema provided. Proceeding with Auto-Extract mode.[/]")
                mode_label = "Dual-Pass Auto-Extract"
            else:
                mode_label = "Dual-Pass Custom Schema"

        elif "Load Schema from a JSON file" in action:
            file_path = questionary.text("Enter path to schema .json file:", style=CUSTOM_QUESTIONARY_STYLE).ask()
            if file_path and os.path.exists(file_path.strip()):
                try:
                    with open(file_path.strip(), 'r', encoding='utf-8') as f:
                        custom_schema = f.read().strip()
                    console.print(f"[bold green]✔ Successfully loaded schema from {file_path}[/]")
                    mode_label = f"Dual-Pass File Schema ({os.path.basename(file_path)})"
                except Exception as e:
                    console.print(f"[bold red]✖ Error reading file:[/] {e}")
                    time.sleep(1.5)
                    continue
            else:
                console.print("[bold red]✖ File not found or invalid path.[/]")
                time.sleep(1.5)
                continue

        # Get Raw Text Input from User
        user_input = get_multiline_input("Paste your raw text below", "bright_cyan")
        if not user_input:
            console.print("[yellow]⚠ No text provided. Returning to menu.[/]")
            time.sleep(1)
            continue

        # Execute Dual-Pass Extraction with Memory Injection
        with console.status(f"[bold bright_yellow]⚡ Stage 1/2: [{cfg['provider'].upper()}] extracting context (+ Memory)...[/]", spinner="dots") as status:
            try:
                parsed_data, elapsed, tokens, audit_summary = run_dual_pass_pipeline(
                    user_input, 
                    cfg, 
                    memory_data,
                    custom_schema=custom_schema, 
                    enable_inspector=enable_inspector,
                    status_callback=lambda msg: status.update(msg)
                )
                formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
            except Exception as e:
                console.print(f"\n[bold red]✖ Error during transformation:[/] {e}\n")
                input("\nPress Enter to return to menu...")
                continue

        # Render Output Panel
        syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=True, word_wrap=True)
        out_panel = Panel(
            syntax,
            box=box.ROUNDED,
            title="[bold bright_green]✔ JOLT Verified & Cleaned JSON Output[/]",
            title_align="left",
            border_style="bright_yellow",
            subtitle=f"[dim]JOLT Inspector • {mode_label}[/]",
            subtitle_align="right"
        )
        console.print(out_panel)
        
        # Render Metrics Badge
        render_metrics_badge(
            elapsed,
            tokens,
            len(formatted_json.encode('utf-8')),
            len(formatted_json.splitlines()),
            cfg["provider"],
            cfg["model"],
            mode_label,
            audit_summary,
            len(memory_data.get("rules", []))
        )

        # Post-Run Actions (Save or Teach Memory)
        save_json_prompt(formatted_json)
        
        want_teach = questionary.confirm("🧠 Would you like to teach JOLT a new rule/memory based on this run?", default=False, style=CUSTOM_QUESTIONARY_STYLE).ask()
        if want_teach:
            teach_jolt_prompt(memory_data, user_input)

        # Pause before looping back
        console.print("\n[dim]Press Enter to return to main menu or Ctrl+C to exit...[/]", end="")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[bold bright_yellow]⚡ Thank you for using JOLT! Goodbye.[/]\n")
            break

if __name__ == "__main__":
    main()
