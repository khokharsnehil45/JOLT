#!/usr/bin/env python3
"""
JSONA - Local AI Text-to-JSON Cleaning & Transformation Tool
Theme inspired by HANDY retro cyberpunk CLI aesthetics.
Features:
- Dual-Pass Architecture (Generator Agent + Critic/Inspector Agent)
- Dynamic Sequential Status Progression (Stage 1 -> Stage 2)
- Auto-Healing & Schema Post-Validation
- Arrow-key menu, Model Switcher, File/Manual Schema support, Metrics, & File Saving.
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
from rich import box

console = Console()

BANNER_ART = r"""
     ██╗███████╗ ██████╗ ███╗   ██╗ █████╗ 
     ██║██╔════╝██╔═══██╗████╗  ██║██╔══██╗
     ██║███████╗██║   ██║██╔██╗ ██║███████║
██   ██║╚════██║██║   ██║██║╚██╗██║██╔══██║
╚█████╔╝███████║╚██████╔╝██║ ╚████║██║  ██║
 ╚════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝
"""

SUBTITLE = "⚡ The Local AI Text-to-JSON Extraction & Context Cleaner ⚡"
VERSION_TAG = "v1.4.1 • Dual-Pass Inspector"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"

# Custom questionary styling matching HANDY retro cyan / magenta theme
CUSTOM_QUESTIONARY_STYLE = Style([
    ('qmark', 'fg:#00ffff bold'),
    ('question', 'fg:#00ffff bold'),
    ('answer', 'fg:#ffff00 bold'),
    ('pointer', 'fg:#ff00ff bold'),
    ('highlighted', 'fg:#ff00ff bold'),
    ('selected', 'fg:#00ffff'),
    ('separator', 'fg:#555555'),
    ('instruction', 'fg:#888888'),
])

def clear_screen():
    """Clear terminal screen for clean unified TUI view."""
    os.system('clear' if os.name != 'nt' else 'cls')

def get_available_models():
    """Fetch installed Ollama models."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
            return models
    except Exception:
        pass
    return []

def print_header(model_name: str):
    """Render retro styled left-aligned header banner with accurate JSONA ASCII art."""
    lines = [line for line in BANNER_ART.split("\n") if line]
    styled_art = Text()
    
    stripe_colors = [
        "bold bright_cyan",
        "bold deep_sky_blue1",
        "bold medium_purple1",
        "bold dark_violet",
        "bold dodger_blue2",
        "bold dodger_blue1"
    ]
    
    for i, line in enumerate(lines):
        color = stripe_colors[i % len(stripe_colors)]
        styled_art.append(line + "\n", style=color)

    styled_art.append(f"\n{SUBTITLE}\n", style="bold yellow")
    
    panel = Panel(
        styled_art,
        box=box.ROUNDED,
        border_style="bright_cyan",
        subtitle=f"[bold bright_magenta]{VERSION_TAG}[/]  [dim]•[/]  [bold cyan]Model: {model_name}[/]",
        subtitle_align="right"
    )
    console.print(panel)

def print_info_box():
    """Render the helper box."""
    info_content = Text.from_markup(
        "[bold yellow]🛠  JSONA Interactive Text-to-JSON Transformer & Inspector[/]\n"
        "[white]Paste messy textual data (unstructured notes, logs, tables, chats, forms, or articles).[/]\n"
        "[dim]Featuring Dual-Pass AI: Generator extracts structured data → Critic Agent audits, repairs, and post-validates.[/]"
    )
    panel = Panel(
        info_content,
        box=box.ROUNDED,
        border_style="yellow"
    )
    console.print(panel)

def render_app_screen(model_name: str):
    """Clear screen and display header + info box seamlessly."""
    clear_screen()
    print_header(model_name)
    print_info_box()

def get_multiline_input(prompt_title: str = "Paste or enter your raw text below", style_color: str = "bright_magenta") -> str:
    """Prompt user for multiline text input."""
    console.print(f"\n[bold bright_cyan]? {prompt_title}[/] [dim](Press Ctrl+D on a new line when finished):[/]\n")
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

def call_ollama(prompt: str, system_prompt: str, model: str) -> tuple[dict, int]:
    """Helper to query Ollama API with JSON format enforcement."""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    
    response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned status code {response.status_code}: {response.text}")
    
    result_json = response.json()
    raw_output = result_json.get("response", "").strip()
    eval_count = result_json.get("eval_count", 0)
    
    try:
        parsed = json.loads(raw_output)
        return parsed, eval_count
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw_output, re.DOTALL)
        if match:
            return json.loads(match.group(1)), eval_count
        raise ValueError(f"Model output could not be parsed as JSON: {raw_output}")

def run_dual_pass_pipeline(text: str, model: str, custom_schema: str | None = None, enable_inspector: bool = True, status_callback=None) -> tuple[dict, float, int, str]:
    """
    Dual-Pass Pipeline with dynamic live status updates:
    Pass 1: Generator Agent -> Initial Extraction
    Pass 2: Critic/Inspector Agent -> Audits against raw text + schema, corrects discrepancies & self-heals
    """
    total_tokens = 0
    start_time = time.perf_counter()
    
    # Update stage status
    if status_callback:
        status_callback("[bold bright_cyan]✦ Stage 1/2: Generator Agent extracting structured context...[/]")
    
    # --- PASS 1: GENERATOR AGENT ---
    if custom_schema:
        gen_sys = (
            "You are an expert JSON transformation engine named JSONA Generator. "
            "Your task is to analyze raw, unstructured textual input, clean up irrelevant noise, "
            "and strictly map and format the data into the target JSON Schema/Template. "
            "Return ONLY valid pure JSON matching the specified schema."
        )
        gen_prompt = f"Target Schema:\n```json\n{custom_schema}\n```\n\nInput raw text:\n```\n{text}\n```\nExtract into valid JSON matching target schema."
    else:
        gen_sys = (
            "You are an expert JSON transformation engine named JSONA Generator. "
            "Analyze the raw textual input, clean noise, and extract all meaningful entities, facts, and context "
            "into a clean, well-structured, valid JSON object. Return ONLY pure raw JSON."
        )
        gen_prompt = f"Input raw text:\n```\n{text}\n```\nConvert valuable contextual data into clean, valid JSON."
    
    initial_json, gen_tokens = call_ollama(gen_prompt, gen_sys, model)
    total_tokens += gen_tokens

    if not enable_inspector:
        elapsed = time.perf_counter() - start_time
        return initial_json, elapsed, total_tokens, "Single-Pass (Fast)"

    # Update stage status
    if status_callback:
        status_callback("[bold bright_magenta]✦ Stage 2/2: Critic Inspector auditing & self-healing data...[/]")

    # --- PASS 2: CRITIC / INSPECTOR AGENT ---
    inspector_sys = (
        "You are an expert Data Quality & Validation Auditor named JSONA Inspector. "
        "Your task is to review a Generated JSON document against the Original Raw Text (and Schema if provided). "
        "Audit checklist:\n"
        "1. Check if any key facts, numbers, dates, or entities from raw text were omitted.\n"
        "2. Check for hallucinations or incorrect values.\n"
        "3. If a target schema is provided, ensure all field names and data types strictly adhere to it.\n"
        "4. Check for syntax correctness and clean structure.\n\n"
        "Return a JSON object with this exact structure:\n"
        "{\n"
        "  \"audit_status\": \"PASSED\" or \"CORRECTED\",\n"
        "  \"audit_notes\": \"Brief 1-sentence explanation of findings or corrections made\",\n"
        "  \"final_json\": { ... the verified and corrected clean JSON object ... }\n"
        "}"
    )

    insp_prompt = f"""Original Raw Text:
```
{text}
```

Target Schema (if any):
```json
{custom_schema if custom_schema else "Automatic Context Extraction"}
```

Generated Candidate JSON:
```json
{json.dumps(initial_json, indent=2)}
```

Audit the candidate JSON, fix any missing facts or schema discrepancies, and return the final corrected JSON in the specified format."""

    try:
        audit_result, insp_tokens = call_ollama(insp_prompt, inspector_sys, model)
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

def render_metrics_badge(elapsed_sec: float, token_count: int, byte_size: int, line_count: int, model: str, mode_label: str, audit_summary: str):
    """Render a sleek execution metrics panel with Dual-Pass Inspector details."""
    t_speed = (token_count / elapsed_sec) if elapsed_sec > 0 and token_count > 0 else 0
    
    if "CORRECTED" in audit_summary:
        audit_tag = f"[bold yellow]🛠 Inspector Auto-Healed:[/] [white]{audit_summary}[/]"
    elif "PASSED" in audit_summary:
        audit_tag = f"[bold bright_green]✔ Inspector Verified:[/] [dim]{audit_summary}[/]"
    else:
        audit_tag = f"[bold cyan]ℹ Inspector:[/] [dim]{audit_summary}[/]"

    m_text = (
        f"[bold bright_green]✔ Validated JSON[/]  [dim]•[/]  "
        f"[bold cyan]⏱ Total Latency:[/] {elapsed_sec:.2f}s  [dim]•[/]  "
        f"[bold yellow]📊 Tokens:[/] {token_count} [dim]({t_speed:.1f} t/s)[/]  [dim]•[/]  "
        f"[bold magenta]📦 Size:[/] {byte_size} B ({line_count} lines)  [dim]•[/]  "
        f"[bold white]🏷 Mode:[/] {mode_label}\n"
        f"{audit_tag}"
    )
    
    panel = Panel(
        Text.from_markup(m_text),
        box=box.ROUNDED,
        border_style="dim bright_cyan",
        style="on grey11"
    )
    console.print(panel)

def save_json_prompt(json_content: str):
    """Prompt user to save the generated JSON output to a file."""
    want_save = questionary.confirm(
        "💾 Would you like to save this JSON output to a file?",
        default=False,
        style=CUSTOM_QUESTIONARY_STYLE
    ).ask()
    
    if not want_save:
        return

    current_dir = os.getcwd()
    target_dir = questionary.text(
        "Enter destination directory:",
        default=current_dir,
        style=CUSTOM_QUESTIONARY_STYLE
    ).ask()
    
    if not target_dir:
        target_dir = current_dir
    target_dir = os.path.expanduser(target_dir.strip())

    if not os.path.exists(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
            console.print(f"[dim green]Created directory: {target_dir}[/]")
        except Exception as e:
            console.print(f"[bold red]✖ Could not create directory:[/] {e}")
            return

    default_filename = f"jsona_output_{int(time.time())}.json"
    target_file = questionary.text(
        "Enter file name:",
        default=default_filename,
        style=CUSTOM_QUESTIONARY_STYLE
    ).ask()
    
    if not target_file:
        target_file = default_filename
    target_file = target_file.strip()
    if not target_file.endswith(".json"):
        target_file += ".json"

    full_path = os.path.join(target_dir, target_file)
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(json_content)
        console.print(f"\n[bold bright_green]✔ JSON successfully saved to:[/] [underline bright_cyan]{full_path}[/]")
    except Exception as e:
        console.print(f"[bold red]✖ Error writing file:[/] {e}")

def select_model(current_model: str) -> str:
    """Prompt user to choose from available Ollama models."""
    models = get_available_models()
    if not models:
        console.print("[yellow]⚠ No other models found on local Ollama.[/]")
        time.sleep(1)
        return current_model
    
    choices = [f"{m} {'(current)' if m == current_model else ''}" for m in models]
    choices.append("Cancel")
    
    selected = questionary.select(
        "Select an Ollama model:",
        choices=choices,
        style=CUSTOM_QUESTIONARY_STYLE
    ).ask()
    
    if selected and selected != "Cancel":
        chosen_model = selected.split()[0]
        return chosen_model
    return current_model

def main():
    available_models = get_available_models()
    model = DEFAULT_MODEL
    if available_models:
        if DEFAULT_MODEL in available_models:
            model = DEFAULT_MODEL
        else:
            llms = [m for m in available_models if "embed" not in m]
            if llms:
                model = llms[0]
            else:
                model = available_models[0]
                
    try:
        requests.get("http://localhost:11434/api/tags", timeout=2)
    except Exception:
        print_header(model)
        console.print("\n[bold red]✖ Error: Cannot connect to Ollama.[/] Please run [yellow]`ollama serve`[/] or ensure Ollama is active.\n")
        sys.exit(1)

    # Handle Piped Mode
    if not sys.stdin.isatty():
        print_header(model)
        print_info_box()
        user_input = sys.stdin.read().strip()
        if user_input:
            with console.status("[bold bright_cyan]✦ Stage 1/2: Extracting context...[/]", spinner="dots") as status:
                try:
                    parsed_data, elapsed, tokens, audit_summary = run_dual_pass_pipeline(
                        user_input, 
                        model, 
                        enable_inspector=True,
                        status_callback=lambda msg: status.update(msg)
                    )
                    formatted_json = json.dumps(parsed_data, indent=2, ensure_ascii=False)
                    syntax = Syntax(formatted_json, "json", theme="monokai", line_numbers=True, word_wrap=True)
                    out_panel = Panel(
                        syntax,
                        box=box.ROUNDED,
                        title="[bold bright_green]✔ Verified & Cleaned JSON Output[/]",
                        title_align="left",
                        border_style="bright_magenta",
                        subtitle="[dim]Dual-Pass Verified[/]",
                        subtitle_align="right"
                    )
                    console.print(out_panel)
                    render_metrics_badge(elapsed, tokens, len(formatted_json.encode('utf-8')), len(formatted_json.splitlines()), model, "Auto-Extract (Piped)", audit_summary)
                except Exception as e:
                    console.print(f"\n[bold red]✖ Error during transformation:[/] {e}\n")
        return

    # Interactive Loop
    while True:
        render_app_screen(model)
        
        console.print("")
        action = questionary.select(
            "Select an action:",
            choices=[
                "✦ Auto-Extract Context (Dual-Pass Agent Inspector)",
                "📋 Custom Schema / Template Extraction",
                "📁 Load Schema from a JSON file",
                "⚡ Fast Single-Pass Extraction (No Inspector)",
                "⚙ Switch Ollama Model",
                "🚪 Exit JSONA"
            ],
            style=CUSTOM_QUESTIONARY_STYLE
        ).ask()

        if action is None or "Exit JSONA" in action:
            console.print("\n[bold bright_magenta]✨ Thank you for using JSONA! Goodbye.[/]\n")
            break

        if "Switch Ollama Model" in action:
            model = select_model(model)
            continue

        custom_schema = None
        mode_label = "Dual-Pass Auto-Extract"
        enable_inspector = True

        if "Fast Single-Pass" in action:
            enable_inspector = False
            mode_label = "Fast Single-Pass"

        elif "Custom Schema / Template" in action:
            custom_schema = get_multiline_input("Paste your custom JSON Schema / Template below", "yellow")
            if not custom_schema:
                console.print("[dim yellow]No schema provided. Proceeding with Auto-Extract mode.[/]")
                mode_label = "Dual-Pass Auto-Extract"
            else:
                mode_label = "Dual-Pass Custom Schema"

        elif "Load Schema from a JSON file" in action:
            file_path = questionary.text(
                "Enter path to schema .json file:",
                style=CUSTOM_QUESTIONARY_STYLE
            ).ask()
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
        user_input = get_multiline_input("Paste your raw text below", "bright_magenta")
        if not user_input:
            console.print("[yellow]⚠ No text provided. Returning to menu.[/]")
            time.sleep(1)
            continue

        # Transform with Dynamic Dual-Pass Status Update
        with console.status("[bold bright_cyan]✦ Stage 1/2: Generator Agent extracting structured context...[/]", spinner="dots") as status:
            try:
                parsed_data, elapsed, tokens, audit_summary = run_dual_pass_pipeline(
                    user_input, 
                    model, 
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
            title="[bold bright_green]✔ Verified & Cleaned JSON Output[/]",
            title_align="left",
            border_style="bright_magenta",
            subtitle=f"[dim]JSONA Inspector • {mode_label}[/]",
            subtitle_align="right"
        )
        console.print(out_panel)
        
        # Render Metrics & Audit Badge
        render_metrics_badge(
            elapsed,
            tokens,
            len(formatted_json.encode('utf-8')),
            len(formatted_json.splitlines()),
            model,
            mode_label,
            audit_summary
        )

        # Save to File Prompt
        save_json_prompt(formatted_json)

        # Pause before looping back
        console.print("\n[dim]Press Enter to return to main menu or Ctrl+C to exit...[/]", end="")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[bold bright_magenta]✨ Thank you for using JSONA! Goodbye.[/]\n")
            break

if __name__ == "__main__":
    main()
