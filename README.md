# Film Breakdown Assistant

A professional, modular Python tool designed for Assistant Directors and film production professionals. This tool leverages local LLMs (via Ollama) to automate the script breakdown process, extracting critical production data for scheduling and logistics.

## 🚀 Overview
The **Film Breakdown Assistant** parses screenplay files (.fdx, .pdf, .docx) and utilizes AI to identify scene elements, safety concerns, and production requirements. It is designed specifically to bridge the gap between creative scripts and professional scheduling software like **Movie Magic Scheduling**.

### Key Features
* **Local AI Processing:** Uses Ollama (Llama 3.2) to ensure script privacy and offline capability.
* **Conservative Extraction Mode:** Distinguishes between explicit script text and AI-implied production needs.
* **Safety & Regulatory Flagging:** Automated alerts for Minors, Intimacy, Stunts, Animals, and Weapons.
* **Industry Standard Export:** Generates `.sex` (Scheduling Export) files for direct import into Movie Magic as well as Excel output.
* **Session Management:** Save and load breakdown progress to pick up exactly where you left off.

## 🛠️ Technical Stack
* **Language:** Python 3.11+
* **UI:** PySide6 (Qt)
* **Intelligence:** Ollama (Llama 3.2 3B)
* **Data Handling:** Pydantic, Pandas

## 📂 Project Structure
* `src/core/`: Parsing, logic, and data models.
* `src/ai/`: Ollama integration and prompt engineering.
* `src/ui/`: PySide6 interface components.

## 🚦 Status
**Planning Phase:** Currently defining core data schemas and skeleton architecture.
