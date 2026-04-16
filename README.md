# AI Repository Analyzer and Architecture Visualizer

Analyze any GitHub repository (Python, JavaScript, TypeScript, Java, Kotlin, Go) and visualize its architecture interactively on your Android phone.

## Architecture

```
📱 Android Phone  ──(Wi-Fi)──▶  💻 Your PC (FastAPI)  ──▶  🤖 Groq Cloud (LLaMA 3)
```

| Component | Tech | Location |
|-----------|------|----------|
| Backend API | Python, FastAPI, NetworkX, Tree-sitter | Your PC |
| AI Engine | Groq API (LLaMA 3) | Cloud |
| Android App | Kotlin, Jetpack Compose | Your phone |

## Supported Languages

| Language | Extensions | Parser |
|----------|-----------|--------|
| Python | `.py` | Built-in AST |
| JavaScript | `.js`, `.jsx` | Tree-sitter |
| TypeScript | `.ts`, `.tsx` | Tree-sitter |
| Java | `.java` | Tree-sitter |
| Kotlin | `.kt` | Tree-sitter |
| Go | `.go` | Tree-sitter |

## Prerequisites

- **Python 3.11+** on your PC
- **Git** installed (for cloning repos)
- **Groq API Key** — get one free at [console.groq.com](https://console.groq.com)
- **Android Studio** (Hedgehog or newer) with SDK 34

---

## 🚀 Quick Start

### Step 1: Start the Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set your Groq API key
set GROQ_API_KEY=gsk_your_key_here        # Windows CMD
# $env:GROQ_API_KEY="gsk_your_key_here"   # Windows PowerShell
# export GROQ_API_KEY=gsk_your_key_here   # macOS/Linux

# Start server (accessible on your Wi-Fi network)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Test it: Open `http://localhost:8000/docs` in your browser.

### Step 2: Find Your PC's IP Address

```bash
ipconfig    # Windows — look for "IPv4 Address" under Wi-Fi (e.g., 192.168.1.5)
# ifconfig  # macOS/Linux
```

### Step 3: Configure the Android App

Open `android/app/src/main/java/com/repoanalyzer/data/api/RetrofitClient.kt`

Change `BASE_URL` to your PC's IP:
```kotlin
private const val BASE_URL = "http://192.168.1.5:8000/"  // ← your PC's IP
```

### Step 4: Build & Install on Phone

1. Open the `android/` folder in **Android Studio**
2. Connect your phone via USB (enable USB Debugging)
3. Click **Run** ▶️
4. The app installs on your phone!

> **Tip:** Make sure your phone and PC are on the **same Wi-Fi network**.

---

## 📱 Using the App

1. Open **Repo Analyzer** on your phone
2. Paste a GitHub repo URL (e.g., `https://github.com/pallets/flask`)
3. Tap **Analyze Repository**
4. Explore:
   - 📊 **Dashboard** — stats, AI summary, and use-case analysis
   - 🔗 **Architecture Graph** — interactive node visualization (pinch to zoom!)
   - 📁 **File Explorer** — browse all files across all languages
   - 🔍 **Inspection** — class/function details with structured AI explanations

---

## API Endpoints

### Core Analysis

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze/github` | Analyze a GitHub repo |
| POST | `/api/analyze/upload` | Analyze a ZIP upload |
| GET | `/api/analysis/{id}` | Full analysis results |
| GET | `/api/analysis/{id}/graph` | Architecture graph |
| GET | `/api/analysis/{id}/files` | File listing |
| GET | `/api/analysis/{id}/file/{path}` | Single file detail |

### AI Explanations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analysis/{id}/explain/{path}` | AI explanation for a file |
| GET | `/api/analysis/{id}/explain-repo` | Repo-level AI explanation |

### Structured Analysis (NEW in v2.0)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analysis/{id}/use-cases` | Structured use-case extraction (actors, use cases, relationships) |
| POST | `/api/analysis/{id}/explain-element` | Code element explanation (purpose, role, notes, category) |
| POST | `/api/analysis/{id}/execution-flow` | Execution flow tracing with AI explanation |

---

## Structured Analysis Output

### A. Use-Case Extraction
Automatically identifies actors, extracts 5–12 high-level use cases, and maps relationships.

```json
{
  "actors": ["User", "Admin", "External API"],
  "use_cases": ["Authenticate user via OAuth", "Upload and analyze repository", ...],
  "relationships": ["User → Authenticate", "Admin → Manage settings", ...],
  "raw_explanation": "..."
}
```

### B. Code Element Explanation
Explains any class or function with structured output:

```json
{
  "name": "GraphBuilder",
  "file_path": "services/graph_builder.py",
  "element_type": "class",
  "purpose": "Constructs a directed graph from AST analysis results...",
  "role": "Core service that transforms flat analysis data into a visual graph...",
  "notes": "Depends on NetworkX. Handles cycle detection internally.",
  "category": "Core Logic"
}
```

### C. Execution Flow Tracing
Traces call paths from any function and explains the flow:

```json
{
  "start_point": "analyze_github",
  "call_path": [
    "analyze_github()  [routers/api.py]",
    "→ clone_github_repo(url)  [services/repo_ingester.py]",
    "→ analyze_repository(repo_path)  [services/ast_analyzer.py]"
  ],
  "flow_explanation": "1. The request handler receives a GitHub URL...\n2. ..."
}
```

---

## Project Structure

```
backend/
├── main.py                  # FastAPI entry point (v2.0)
├── config.py                # Settings (Groq key, multi-lang extensions)
├── requirements.txt
├── routers/api.py           # REST endpoints (11 routes)
├── services/
│   ├── repo_ingester.py     # GitHub clone + ZIP extract
│   ├── ast_analyzer.py      # Python AST parsing + multi-lang dispatch
│   ├── generic_analyzer.py  # Tree-sitter analyzer (JS/TS/Java/Kotlin/Go)
│   ├── graph_builder.py     # NetworkX graph construction
│   ├── ai_explainer.py      # Structured AI explanations (Groq LLaMA 3)
│   └── flow_tracer.py       # Execution flow call-path tracer
├── models/
│   ├── graph_models.py      # Node, Edge, Analysis dataclasses
│   └── schemas.py           # Pydantic API schemas (11 models)
└── utils/helpers.py         # Filesystem utilities

android/app/src/main/java/com/repoanalyzer/
├── MainActivity.kt          # App entry + navigation
├── viewmodel/AnalysisViewModel.kt
├── data/
│   ├── api/ApiService.kt, RetrofitClient.kt
│   ├── models/Models.kt
│   └── repository/AnalysisRepository.kt
└── ui/
    ├── theme/Theme.kt
    └── screens/
        ├── HomeScreen.kt         # Repo URL input
        ├── AnalysisScreen.kt     # Dashboard
        ├── GraphScreen.kt        # Architecture graph
        ├── FileExplorerScreen.kt # File browser
        └── InspectionScreen.kt   # Code inspection
```

---

## What's New in v2.0

| Feature | Description |
|---------|-------------|
| 🌐 Multi-language support | Analyze Python, JS/TS, Java, Kotlin, Go in one repo |
| 🎯 Use-case extraction | AI identifies actors, use cases, and relationships |
| 🔍 Code element explanation | Structured Purpose/Role/Notes/Category for any element |
| 🔄 Execution flow tracing | Call-path analysis with step-by-step AI explanation |
| 🛡️ Retry logic | LLM calls retry with exponential backoff |
| 📝 Structured logging | Full request/analysis lifecycle logging |

## Advanced Features (Future Roadmap)

| Feature | Description |
|---------|-------------|
| 🔄 Circular dependency detection | Detect import cycles in the graph |
| 🏗️ Architecture smell detection | Flag god classes, high fan-out |
| 💥 Impact analysis | Show what breaks when a file changes |
| 📤 Export | PNG/SVG export of architecture diagrams |
| 📱 ZIP upload | Upload projects directly from phone |
