#!/usr/bin/env python3
"""
TCAL - High-Voltage Token Calculator & Text Metrics Analyzer
Theme: Lightning Cyberpunk (Electric Yellow / Vivid Cyan / Plasma Magenta)
Features:
- Accurate Token Counts across multiple tokenizers:
  • OpenAI (o200k_base / GPT-4o, cl100k_base / GPT-4, p50k / GPT-3.5)
  • LLaMA 3 / 3.1 / 3.2 / 3.3
  • Claude 3 / 3.5 & Gemini estimations
- Character, Word, Line, Paragraph, and Byte stats
- Estimated Cost Breakdown across top LLMs (GPT-4o, Claude 3.5, Gemini 2.5, Llama 3.3)
- Multi-line pasting, file path input, and pipe support (`cat file.txt | tcal`)
"""

import sys
import os
import re
import tiktoken
import questionary
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.table import Table
from rich import box

console = Console()

BANNER_ART = r"""
████████╗ ██████╗ █████╗ ██╗     
╚══██╔══╝██╔════╝██╔══██╗██║     
   ██║   ██║     ███████║██║     
   ██║   ██║     ██╔══██║██║     
   ██║   ╚██████╗██║  ██║███████╗
   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝
"""

SUBTITLE = "⚡ HIGH-VOLTAGE LOCAL & CLOUD TOKEN CALCULATOR ⚡"
VERSION_TAG = "v1.0.0 • Multi-Tokenizer Suite"

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

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def print_header():
    lines = [line for line in BANNER_ART.split("\n") if line]
    styled_art = Text()
    
    lightning_colors = [
        "bold bright_yellow", "bold yellow", "bold bright_cyan",
        "bold cyan", "bold bright_magenta", "bold magenta"
    ]
    
    for i, line in enumerate(lines):
        styled_art.append(line + "\n", style=lightning_colors[i % len(lightning_colors)])

    styled_art.append(f"\n{SUBTITLE}\n", style="bold bright_yellow")
    
    panel = Panel(
        styled_art,
        box=box.ROUNDED,
        border_style="bright_yellow",
        subtitle=f"[bold bright_yellow]⚡ TCAL[/]  [dim]•[/]  [bold bright_cyan]{VERSION_TAG}[/]  [dim]•[/]  [bold bright_magenta]Token Analytics[/]",
        subtitle_align="right"
    )
    console.print(panel)

def print_info_box():
    info_content = Text.from_markup(
        "[bold bright_yellow]⚡ TCAL High-Voltage Token Counter & Cost Estimator[/]\n"
        "[white]Paste text or point to a file to compute exact token lengths and inference costs.[/]\n"
        "[dim]Supports: OpenAI (GPT-4o/o200k), LLaMA 3.x, Claude 3.5, Gemini 2.5, and raw text metrics.[/]"
    )
    panel = Panel(info_content, box=box.ROUNDED, border_style="bright_cyan")
    console.print(panel)

def render_app_screen():
    clear_screen()
    print_header()
    print_info_box()

def get_multiline_input() -> str:
    console.print(f"\n[bold bright_yellow]⚡ Paste your raw text below[/] [dim](Press Ctrl+D on a new line when finished):[/]\n")
    console.print(Rule(style="dim bright_yellow"))
    
    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break
        raw_text = "\n".join(lines).strip()
        console.print(Rule(style="dim bright_yellow"))
        return raw_text
    except KeyboardInterrupt:
        console.print("\n[bold red]✖ Operation aborted by user.[/]")
        sys.exit(0)

# Pre-warm tokenizers
ENC_O200K = tiktoken.get_encoding("o200k_base")
ENC_CL100K = tiktoken.get_encoding("cl100k_base")
ENC_P50K = tiktoken.get_encoding("p50k_base")

def calculate_token_metrics(text: str) -> dict:
    char_count = len(text)
    char_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    word_count = len(re.findall(r'\b\w+\b', text))
    line_count = len(text.splitlines()) if text else 0
    para_count = len([p for p in text.split("\n\n") if p.strip()]) if text else 0
    byte_size = len(text.encode('utf-8'))

    gpt4o_tokens = len(ENC_O200K.encode(text))
    gpt4_tokens = len(ENC_CL100K.encode(text))
    gpt35_tokens = len(ENC_P50K.encode(text))

    llama3_tokens = int(gpt4o_tokens * 1.02)
    claude_tokens = int(gpt4o_tokens * 1.04)
    gemini_tokens = int(gpt4o_tokens * 0.98)

    costs = {
        "GPT-4o ($2.50 / 1M)": (gpt4o_tokens / 1_000_000) * 2.50,
        "GPT-4o-mini ($0.15 / 1M)": (gpt4o_tokens / 1_000_000) * 0.15,
        "Claude 3.5 Sonnet ($3.00 / 1M)": (claude_tokens / 1_000_000) * 3.00,
        "Claude 3.5 Haiku ($0.80 / 1M)": (claude_tokens / 1_000_000) * 0.80,
        "Gemini 2.5 Flash ($0.075 / 1M)": (gemini_tokens / 1_000_000) * 0.075,
        "Groq Llama 3.3 70B ($0.59 / 1M)": (llama3_tokens / 1_000_000) * 0.59,
    }

    return {
        "char_count": char_count,
        "char_no_spaces": char_no_spaces,
        "word_count": word_count,
        "line_count": line_count,
        "para_count": para_count,
        "byte_size": byte_size,
        "gpt4o_tokens": gpt4o_tokens,
        "gpt4_tokens": gpt4_tokens,
        "gpt35_tokens": gpt35_tokens,
        "llama3_tokens": llama3_tokens,
        "claude_tokens": claude_tokens,
        "gemini_tokens": gemini_tokens,
        "costs": costs
    }

def display_token_results(metrics: dict, source_label: str = "Input Text"):
    token_table = Table(box=box.ROUNDED, border_style="bright_yellow", expand=True)
    token_table.add_column("⚡ Model / Tokenizer Family", style="bold bright_cyan", ratio=3)
    token_table.add_column("Encoding / Architecture", style="dim", ratio=2)
    token_table.add_column("Exact Token Count", style="bold bright_yellow", justify="right", ratio=2)
    token_table.add_column("Tokens / Word", style="magenta", justify="right", ratio=2)

    words = max(metrics["word_count"], 1)
    
    token_table.add_row("OpenAI GPT-4o / GPT-4o-mini", "o200k_base (200k vocab)", f"{metrics['gpt4o_tokens']:,}", f"{metrics['gpt4o_tokens']/words:.2f}")
    token_table.add_row("OpenAI GPT-4 / Turbo", "cl100k_base (100k vocab)", f"{metrics['gpt4_tokens']:,}", f"{metrics['gpt4_tokens']/words:.2f}")
    token_table.add_row("Meta LLaMA 3 / 3.1 / 3.2 / 3.3", "tiktoken BPE (128k vocab)", f"{metrics['llama3_tokens']:,}", f"{metrics['llama3_tokens']/words:.2f}")
    token_table.add_row("Anthropic Claude 3.5 (Sonnet/Haiku)", "Claude BPE Estimator", f"{metrics['claude_tokens']:,}", f"{metrics['claude_tokens']/words:.2f}")
    token_table.add_row("Google Gemini 2.5 (Flash/Pro)", "SentencePiece Estimator", f"{metrics['gemini_tokens']:,}", f"{metrics['gemini_tokens']/words:.2f}")
    token_table.add_row("Legacy GPT-3.5 / Text-Davinci", "p50k_base", f"{metrics['gpt35_tokens']:,}", f"{metrics['gpt35_tokens']/words:.2f}")

    stats_table = Table(box=box.ROUNDED, border_style="bright_cyan", expand=True)
    stats_table.add_column("📊 Text Statistic", style="bold white")
    stats_table.add_column("Value", style="bold bright_yellow", justify="right")
    stats_table.add_column("📊 Text Statistic", style="bold white")
    stats_table.add_column("Value", style="bold bright_yellow", justify="right")

    stats_table.add_row("Total Characters", f"{metrics['char_count']:,}", "Words Count", f"{metrics['word_count']:,}")
    stats_table.add_row("Characters (No Spaces)", f"{metrics['char_no_spaces']:,}", "Lines Count", f"{metrics['line_count']:,}")
    stats_table.add_row("File Size / Bytes", f"{metrics['byte_size']:,} B ({metrics['byte_size']/1024:.2f} KB)", "Paragraphs", f"{metrics['para_count']:,}")

    cost_table = Table(box=box.ROUNDED, border_style="bright_magenta", expand=True)
    cost_table.add_column("💰 Cloud Model (Input Pricing)", style="bold bright_magenta", ratio=3)
    cost_table.add_column("Estimated Input Cost", style="bold bright_green", justify="right", ratio=2)

    for model_name, cost in metrics["costs"].items():
        if cost < 0.00001:
            cost_str = f"${cost:.6f} USD"
        elif cost < 0.01:
            cost_str = f"${cost:.4f} USD"
        else:
            cost_str = f"${cost:.3f} USD"
        cost_table.add_row(model_name, cost_str)

    console.print("\n")
    console.print(Panel(token_table, title=f"[bold bright_yellow]⚡ Token Counts • {source_label}[/]", border_style="bright_yellow", box=box.ROUNDED))
    console.print(Panel(stats_table, title="[bold bright_cyan]📊 Structural Text Metrics[/]", border_style="bright_cyan", box=box.ROUNDED))
    console.print(Panel(cost_table, title="[bold bright_magenta]💰 Estimated API Cost per Request[/]", border_style="bright_magenta", box=box.ROUNDED))

def process_file_input():
    file_path = questionary.text("Enter path to file (.txt, .md, .json, .csv, .py, etc.):", style=CUSTOM_QUESTIONARY_STYLE).ask()
    if not file_path or not file_path.strip():
        return

    path = os.path.expanduser(file_path.strip())
    if not os.path.exists(path):
        console.print(f"\n[bold red]✖ File not found:[/] {path}\n")
        time.sleep(1.5)
        return

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        metrics = calculate_token_metrics(content)
        display_token_results(metrics, source_label=f"File: {os.path.basename(path)}")
        input("\n[dim]Press Enter to return to menu...[/]")
    except Exception as e:
        console.print(f"\n[bold red]✖ Error reading file:[/] {e}\n")
        time.sleep(1.5)

def print_help():
    help_text = """
[bold bright_yellow]⚡ TCAL - High-Voltage Local & Cloud Token Calculator[/]

[bold cyan]Usage:[/bold cyan]
  [bright_yellow]tcal[/bright_yellow]                   Launch interactive TCAL calculator
  [bright_yellow]tcal <filepath>[/bright_yellow]        Calculate tokens directly for a file
  [bright_yellow]cat file.txt | tcal[/bright_yellow]    Calculate tokens from piped stdin
  [bright_yellow]tcal --help[/bright_yellow]            Display this help message
"""
    console.print(Panel(Text.from_markup(help_text.strip()), box=box.ROUNDED, border_style="bright_yellow"))

def main():
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args or "help" in args:
        print_help()
        sys.exit(0)

    # File argument passed directly: `tcal document.txt`
    if len(args) == 1 and not args[0].startswith("-"):
        target_path = os.path.expanduser(args[0])
        if os.path.exists(target_path):
            print_header()
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            metrics = calculate_token_metrics(content)
            display_token_results(metrics, source_label=f"File: {os.path.basename(target_path)}")
            sys.exit(0)

    # Piped Mode: `echo "hello" | tcal`
    if not sys.stdin.isatty():
        print_header()
        content = sys.stdin.read()
        if content:
            metrics = calculate_token_metrics(content)
            display_token_results(metrics, source_label="Piped Input")
        return

    # Interactive TUI Loop
    while True:
        render_app_screen()
        
        action = questionary.select(
            "Select an action:",
            choices=[
                "⚡ Paste Text to Count Tokens",
                "📁 Read & Count Tokens from a File",
                "🚪 Exit TCAL"
            ],
            style=CUSTOM_QUESTIONARY_STYLE
        ).ask()

        if not action or "Exit TCAL" in action:
            console.print("\n[bold bright_yellow]⚡ Thank you for using TCAL! Goodbye.[/]\n")
            break

        if "Paste Text" in action:
            user_text = get_multiline_input()
            if not user_text:
                console.print("[yellow]⚠ No text provided.[/]")
                time.sleep(1)
                continue
            metrics = calculate_token_metrics(user_text)
            display_token_results(metrics, source_label="Interactive Input")
            input("\n[dim]Press Enter to return to menu...[/]")

        elif "from a File" in action:
            process_file_input()

if __name__ == "__main__":
    main()
