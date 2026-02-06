# Film Breakdown Assistant

**Film Breakdown Assistant** is an intelligent production-scheduling utility designed to eliminate the labor-intensive "grunt work" of manual script analysis. By leveraging Local LLMs, the tool provides a security-first environment for sensitive IP, extracting critical production variables; department elements, stunts, intimacy, and safety requirements—directly into industry-standard formats.

## Project Status
🚦 **Project Status:** Alpha (Active Development)
The core logic is currently functional via CLI, utilizing Pydantic for data validation and Pandas for structured output.
**Current Output:** Automated Excel-based breakdown sheets.
**Next Milestone:** Implementing .sex (Scheduling Export) support to enable direct, one-click ingestion into Movie Magic Scheduling, eliminating the need for manual data re-entry.

## Strategic Roadmap
* **Phase 1 (Current):** Refine CLI-based parsing for .fdx and .pdf; optimize Llama 3.2 prompt strategies for "Conservative Extraction" of safety and regulatory flags; implement Supervisor Agent v1 for element reconciliation and continuity auditing.
* **Phase 2 (Immediate):** Develop the .sex export module; integrate AD Alert custom categories for Movie Magic Scheduling.
* **Phase 3 (Q1 2026):** Transition to a PySide6 (Qt) interface for professional session management and local database persistence.

## 🚀 Overview
The **Film Breakdown Assistant** is a professional-grade utility designed to eliminate the manual "heavy lifting" of the script breakdown process. By automating the extraction of 80%+ of repetitive "grunt work," it empowers Assistant Directors and Production Managers to shift their focus from rote data entry to high-level logistical strategy and creative problem-solving.

The tool follows a **"Security-First"** and **"Human-in-the-Loop"** philosophy:
1. **Local AI:** All processing happens offline via Ollama, ensuring sensitive IP never leaves the local machine.
2. **Professional Oversight:** AI performs the initial analysis, while a dedicated **Review & Validation UI** ensures the professional maintains final authority over the data before it enters the production pipeline.

## 🛠️ Key Features

* **Intelligence-Driven Script Parsing:** Extracts industry-standard metadata, including slugline parsing (INT/EXT, Location, Time of Day), page count duration in 1/8ths, and automated 6-word scene synopses.
* **Agentic Continuity Audit:** Goes beyond scene-by-scene analysis using a secondary Supervisor Agent pass. This reasoning layer ensures story-wide consistency, reconciling generic terms (e.g., "Car") with established specifics (e.g., "1967 MUSTANG") and tracking physical states like wounds or wardrobe changes across continuous scenes.
* **Security-First Local Processing:** Utilizes **Ollama** (Llama 3.2) for 100% offline AI analysis, ensuring sensitive, unreleased intellectual property never leaves the local machine.
* **Comprehensive Element Extraction:** Leverages LLM analysis to identify and categorize 15+ production departments, from Cast and Background counts to Props, Vehicles, and VFX requirements.
* **Automated Risk & Safety Flagging:** Scans for high-priority production concerns, including regulatory labor (minors), stunts, intimacy, weaponry, and high-cost logistics (animals/cranes).
* **Conservative vs. Inference Modes:** Toggleable extraction logic that distinguishes between explicitly stated script elements and AI-implied production needs (e.g., implying "SFX: Smoke" if "Fire" is mentioned).
* **Hardware-Optimized Workflows:** Features "Eco" and "Power" processing modes to manage local compute resources, enabling smooth operation on production laptops or high-speed multi-threaded analysis.
* **Industry Standard Interoperability:** Engineered for direct integration into the production ecosystem with planned **.sex (Scheduling Export)** support for **Movie Magic Scheduling** alongside Excel/CSV output.
* **Session & State Management:** Includes robust "Save/Load" functionality via local JSON checkpoints, allowing production staff to review, edit, and resume breakdowns without data loss.

## 🧠 Advanced Workflows: The Supervisor Agent
Unlike standard extractors that treat scenes in isolation, this tool utilizes an Agentic Reasoning Loop. Once the initial extraction is complete, a dedicated Supervisor Agent performs a panoramic audit of the entire script:
* **Global World State:** The agent compiles a "Global Context" of all named characters, unique vehicles, and key props to prevent "data drift."
* **Implicit Element Discovery:** Scans character dialogue for props mentioned but not explicitly described in action lines.
* **Continuity Intelligence:** Recognizes CONTINUOUS and SAME time-of-day markers to ensure that character makeup (wounds/aging) and wardrobe conditions persist logically between scenes.
* **AD Alerts (Custom Category):** Automatically generates high-priority production alerts for safety and regulatory concerns, ready for dedicated ingestion into scheduling software.

## 🛠️ Technical Stack
* **Language:** Python 3.11+
* **UI:** PySide6 (Qt)
* **Intelligence:** Ollama (Llama 3.2 3B)
* **Data Handling:** Pydantic, Pandas

## 📂 Project Structure
* `src/core/`: Parsing, logic, data models and supervisor agent.
* `src/ai/`: Ollama integration and prompt engineering.
* `src/ui/`: PySide6 interface components.

