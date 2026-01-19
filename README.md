# 🚀 LLMark: Comprehensive Local LLM Benchmarking

LLMark is a powerful, local benchmarking suite for Large Language Models (LLMs) running via **Ollama**. It combines precise hardware performance metrics with high-level qualitative analysis using an automated "Judge-in-the-Loop" architecture.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI-orange.svg)](https://ollama.ai/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

---

## ✨ Key Features

-   **⚡ Live VRAM Monitoring**: Dashboard updates every 2 seconds, showing real-time VRAM usage for both NVIDIA and AMD GPUs.
-   **📈 Precision Throughput (TPS)**: Benchmark A measures actual token generation speed (Tokens Per Second) with a dedicated warmup phase.
-   **🤖 Automated AI Judge**: Benchmarks B-J are evaluated by a sophisticated judge model (`qwen2.5:14b-instruct`) on a scale of 1-10, providing objective scoring and detailed feedback.
-   **🎨 Premium Dark UI**: A fluid, responsive desktop interface built with PySide6, featuring background threading to keep the experience lag-free during intense hardware tests.
-   **🔍 Detailed Insights**: Access raw model responses, judge reasoning, and hardware metrics for every test.
-   **📂 Result Archiving**: Every run is saved as a structured JSON file in the `/results` directory for historical tracking.

---

## 🏗️ Benchmark Suite Overview

LLMark tests models across 10 specialized categories:

| ID | Category | Description |
| :--- | :--- | :--- |
| **A** | **Speed** | Measures throughput (Tokens/sec) using a long generation task. |
| **B** | **English Quality** | Writing a formal business email with 10+ specific facts. |
| **C** | **German Quality** | Drafting a formal "Mahnung" (payment reminder) in German. |
| **D** | **Fact Checking** | Multi-fact verification across history, science, and geography. |
| **E** | **Context** | Information extraction and summarization from meeting transcripts. |
| **F** | **Logic** | Solving complex constraint-satisfaction problems (Timetabling). |
| **G** | **Creativity** | Narrative storytelling in a Cyberpunk-Noir setting with fixed terms. |
| **H** | **ELI5** | Explaining Quantum Entanglement to an 8-year-old child. |
| **I** | **Programming** | Writing robust, documentated Python code for password validation. |
| **J** | **Roleplay** | Empathic de-escalation in a customer support scenario. |

---

## ⚙️ Prerequisites

1.  **Python 3.11+**
2.  **Ollama** installed and running.
3.  **Hardware**: A GPU with sufficient VRAM to run your target model and the **Judge Model** simultaneously (or sequentially).
4.  **Judge Model**: You must have `qwen2.5:14b-instruct` pulled in Ollama.
    ```bash
    ollama pull qwen2.5:14b-instruct
    ```

---

## 🚀 Installation & Setup

### Automatic Setup (Windows & Linux/macOS)
The repository includes scripts that automatically handle environment creation, dependency installation, and even checking for/installing Ollama.

- **Windows**: Run `start.bat`
- **Linux/macOS**: Run `start.sh`

### Manual Setup
1.  **Clone the Repository**
    ```bash
    git clone https://github.com/SnowTimSwiss/LLMark.git
    cd LLMark
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python app.py
    ```

---

## 🤖 Auto-Pilot Mode (Easiest Way)

For users who want to benchmark multiple models and contribute to the community rankings without manual effort, we provide the **Auto-Pilot Mode**.

### 🌟 Features:
-   **Automated Testing**: Downloads, runs, and evaluates a curated list of popular models (Llama, Qwen, Gemma, DeepSeek, etc.).
-   **Direct Contribution**: Automatically uploads results to the [LLMark-Site](https://github.com/SnowTimSwiss/LLMark-Site) repository via Pull Request.
-   **One-Click Cleanup**: Option to automatically uninstall Ollama and all downloaded models (saving GBs of space) once the run is finished.

### 🏃 How to run Auto-Pilot:
1.  **Generate a GitHub Token**: Go to [GitHub Tokens](https://github.com/settings/tokens/new) and create a "Classic" token with the `public_repo` scope.
2.  **Run the script**:
    -   **Windows**: Just double-click **`autopilot.bat`**.
3.  **Follow the prompts**: Paste your token and decide if you want to keep Ollama after the test.
   
1.  **One-klick-install**
    ```bash
    git clone https://github.com/SnowTimSwiss/LLMark.git
    cd LLMark
    ./autopilot.bat
    ```
---

## 🎮 How to Use

1.  **Select Model**: Choose the LLM you want to benchmark from the dropdown (fetched automatically from your local Ollama library).
2.  **Start Benchmark**: Hit the "Start Benchmark" button.
3.  **Monitor**: Watch the progress bar and real-time VRAM usage. Check the **"Detail-Log"** tab for live output from the model and the judge.
4.  **Analyze**: Review the final scores (out of 90 for qualitative tests + TPS score).
5.  **Export**: Results are automatically saved to the `results/` folder for every run.

---

## 🛠️ Architecture

LLMark uses a **dual-model setup**:
-   **Target Model**: The model you are testing.
-   **Judge Model**: `qwen2.5:14b-instruct` acts as a "fixed reference" to evaluate the Target Model's output quality based on strict rubrics.

> [!NOTE]
> The total score (max 90) is calculated based on the quality benchmarks (B-J). Speed (A) is reported separately as an absolute metric.

---

## 📜 License

Distributed under the GNU General Public License v3.0. See `LICENSE` for more information.

---

*Built for the local LLM community. Happy Benchmarking!* 🚀

