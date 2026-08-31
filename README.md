<div align="center">

```
     ██╗ ██████╗ ██╗  ████████╗
     ██║██╔═══██╗██║  ╚══██╔══╝
     ██║██║   ██║██║     ██║   
██   ██║██║   ██║██║     ██║   
╚█████╔╝╚██████╔╝███████╗██║   
 ╚════╝  ╚═════╝ ╚══════╝╚═╝   
```

### ⚡ HIGH-VOLTAGE AI TEXT-TO-JSON EXTRACTION & MEMORY ENGINE ⚡

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20LLMs-cyan.svg)](https://ollama.ai)
[![Groq](https://img.shields.io/badge/Groq-500%2B%20t%2Fs-magenta.svg)](https://groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*Transform messy, unstructured, multi-page textual data into pristine, strongly-typed, programmatic JSON with zero hallucinations and continuous adaptive learning.*

---

</div>

## ⚡ Overview

**JOLT** is an agentic, dual-pass command-line tool built for developers, data engineers, and AI workflows. It bridges the gap between chaotic text inputs (medical records, server incidents, legal notes, invoice receipts, support chats) and strictly validated, clean JSON structures.

Powered by a **Dual-Pass Agent Architecture** (Generator + Critic Inspector) with **Adaptive Memory Injection**, JOLT guarantees:
- **Zero Data-in-Keys Anti-Patterns**: Never drops text into dictionary keys mapped to `null`.
- **Atomic Entity Decomposition**: Every person, facility, medication, vitals metric, and discount is cleanly broken down into typed fields.
- **Hermetic Extraction Boundary**: No UI flags, prompt leakages, or meta-comments in outputs.
- **Continuous Learning (Memory Engine)**: Automatically remembers your custom domain guidelines, date formats, and naming preferences across sessions.

---

## ⚡ Architecture: The Dual-Pass Pipeline

```
                       Raw Unstructured Text
                                 │
                 ┌───────────────┴───────────────┐
                 │  + Dynamic Memory Injection   │
                 │  (Learned Rules & Prefs)      │
                 └───────────────┬───────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │   Stage 1: GENERATOR  │
                     │  (Context Extraction) │
                     └───────────┬───────────┘
                                 │ Candidate JSON
                                 ▼
                     ┌───────────────────────┐
                     │   Stage 2: CRITIC     │
                     │  (Inspector & Auditor)│
                     └───────────┬───────────┘
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
    [100% Faithful]                        [Discrepancy / Gap]
             │                                       │
             │                                       ▼
             │                              [Auto-Heal / Repair]
             └───────────────────┬───────────────────┘
                                 ▼
                 ✔ Verified, Programmatic JSON
                 + Live Telemetry & Metrics Badge
```

---

## ⚡ Supported AI Engines

JOLT seamlessly switches between local privacy-first models and ultra-fast cloud inference:

| Engine | Supported Models | Description |
| :--- | :--- | :--- |
| **🖥 Local Ollama** | `llama3.2`, `mistral`, `qwen2.5`, `phi3` | 100% offline, private local processing. |
| **⚡ Groq Cloud** | `openai/gpt-oss-120b`, `qwen3.8-27b` | Lightning fast cloud inference (**500+ tokens/sec**). |
| **🌐 Google Gemini** | `gemini-2.5-flash`, `gemini-2.5-pro` | Large context windows and deep reasoning. |
| **🌐 OpenAI** | `gpt-4o-mini`, `gpt-4o`, `o3-mini` | Industry standard accuracy. |
| **🌐 Anthropic** | `claude-3-5-sonnet`, `claude-3-5-haiku` | Elite structured extraction capability. |
| **🌐 OpenRouter** | Any OpenRouter model endpoint | Multi-provider fallback gateway. |

---

## ⚡ Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/khokharsnehil45/JOLT.git
cd JOLT
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 3. Make JOLT Globally Executable
```bash
mkdir -p ~/.local/bin
ln -sf $(pwd)/jolt_launcher.sh ~/.local/bin/jolt
```
*Ensure `~/.local/bin` is in your `$PATH`.*

---

## ⚡ Usage

### Interactive TUI Mode:
```bash
jolt run
```
*(or simply `jolt`)*

### Unix Pipe Mode:
```bash
echo "Invoice #8849: 2x GPUs for \$4,800 to Acme Corp. Status: Paid." | jolt
```

---

## ⚡ Key Features & Capabilities

### 1. 🧠 Adaptive Neural Memory Hub
Teach JOLT your exact preferences once, and it will apply them across all extractions:
- `jolt` $\rightarrow$ Select `🧠 JOLT Memory Hub`
- Add custom rules like:
  - *"Always place all financial totals and currency fields inside a `billing_summary` object."*
  - *"Format all phone numbers with country codes."*
  - *"Preserve timestamps as ISO-8601 strings (YYYY-MM-DD)."*

### 2. 📋 Target Schema Enforcement
- **Auto-Extract**: JOLT determines the optimal schema structure based on data context.
- **Custom Schema (Manual)**: Paste a custom JSON template or schema interactively.
- **File-Based Schema**: Load a `.json` schema file directly from disk.

### 3. 💾 Built-in File Exporter
Promptly saves the output JSON to any specified directory and file name, automatically handling directory creation.

### 4. 📊 Real-Time Telemetry Badge
Every extraction reports:
- **`⏱ Total Latency`** (e.g. `2.84s`)
- **`📊 Token Speed`** (e.g. `530.9 tokens/sec`)
- **`📦 Output Size`** (e.g. `2,180 bytes / 82 lines`)
- **`🧠 Memory Status`** (Active rule count)
- **`🛠 Inspector Audit Findings`** (`PASSED` or `CORRECTED`)

---

## ⚡ Example Benchmark

### Input (Raw Clinical Record):
```text
CLINICAL CONSULTATION & PRIOR-AUTHORIZATION REQUEST
Date of Visit: August 28, 2026 | Facility: Metro General Hospital (NPI: 1049281102)
Physician: Dr. Aris Thorne, MD (Cardiology, License: CA-99201)
Patient: Evelyn Rose Vance (DOB: 1981-04-14, Age: 45, Gender: Female, MRN: MRN-8829104-B)
Vitals: BP: 148/92 mmHg (Grade 1 Essential Hypertension, ICD-10: I10), Total Cholesterol: 238 mg/dL (Hyperlipidemia, ICD-10: E78.5)
Medications:
1. Atorvastatin 20mg Tablet | 1 tab daily at bedtime | Dispense: 90 days | Refills: 3
2. Amlodipine Besylate 5mg Tablet | 1 tab each morning | Dispense: 90 days | Refills: 3
Follow-up: Scheduled 2026-11-20 for repeat lipid panel and ALT liver enzymes.
```

### JOLT Output (Gold-Standard Verified JSON):
```json
{
  "metadata": {
    "date_of_visit": "2026-08-28",
    "facility": {
      "name": "Metro General Hospital",
      "npi": "1049281102"
    }
  },
  "patient": {
    "full_name": "Evelyn Rose Vance",
    "dob": "1981-04-14",
    "age": 45,
    "gender": "Female",
    "mrn": "MRN-8829104-B"
  },
  "physician": {
    "name": "Dr. Aris Thorne, MD",
    "specialty": "Cardiology",
    "license": "CA-99201"
  },
  "diagnoses": [
    {
      "condition": "Grade 1 Essential Hypertension",
      "icd_10": "I10"
    },
    {
      "condition": "Hyperlipidemia",
      "icd_10": "E78.5"
    }
  ],
  "medications": [
    {
      "name": "Atorvastatin",
      "strength": "20mg",
      "form": "Tablet",
      "instructions": "1 tab daily at bedtime",
      "dispense_days": 90,
      "refills": 3
    },
    {
      "name": "Amlodipine Besylate",
      "strength": "5mg",
      "form": "Tablet",
      "instructions": "1 tab each morning",
      "dispense_days": 90,
      "refills": 3
    }
  ],
  "follow_up": {
    "date": "2026-11-20",
    "tests_required": "repeat lipid panel and ALT liver enzymes"
  }
}
```

---

## ⚡ License

MIT License. Crafted with ⚡ for high-voltage AI workflows.
