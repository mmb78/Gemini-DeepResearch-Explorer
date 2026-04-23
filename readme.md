# 🕵️‍♂️ Gemini DeepResearch Explorer

An interactive, feature-rich Streamlit graphical interface for Google's **Gemini Deep Research API**. 

This application transforms the powerful, asynchronous Gemini Interactions API into a sleek conversational workspace. Designed for heavy-duty research tasks, it allows you to collaboratively plan, watch the agent's "thoughts" stream in real-time, recover complex multi-turn sessions, attach multimodal files, and export your final reports (complete with inline charts and graphs) into portable formats. 

Built with resilience in mind, the app features auto-reconnection for long-running streams and deep diagnostic tools for developers.

## ✨ Key Features

* **Two-Stage Workflow:** Don't just prompt and pray. Use **Plan / Refine** mode to brainstorm and outline with the agent, then switch to **Execute** to unleash the full research capabilities.
* **Live Thought Streaming & Resilient Connection:** Watch the agent's internal monologue in real-time as it searches the web, reads documents, and synthesizes data. Features an auto-reconnecting stream to survive network blips during multi-hour tasks.
* **Advanced Session Recovery:** Close your browser or experience a crash? No problem. Paste an Interaction ID to **Recover Last Turn** or instantly trace and **Recover Full Chat** history.
* **Multimodal Attachments:** Securely upload and attach Images, Audio, Video, and Documents directly to your prompts using the native Gemini File API integration. 
* **Granular Tool Control & MCP Support:** Toggle Web Search, Code Execution, and URL Reading on the fly. Connect directly to enterprise or local APIs using custom **MCP (Model Context Protocol) Server** URLs.
* **Agent Configuration:** Dynamically enable or disable "Thinking Summaries" and autonomous "Visualization" (embedded Python chart generation).
* **Rich Exports & Diagnostics:** * Export reports as styled **HTML** (with embedded base64 images for true portability) or **Markdown**.
    * Download a **ZIP** of all raw JSON interaction payloads.
    * View inline **Token Usage Stats** (Input, Output, Thought, Total) and inspect truncated raw JSON responses directly in the UI.
* **Model Toggling:** Easily switch between the lightning-fast Preview model (`deep-research-preview-04-2026`) and the comprehensive Max model (`deep-research-max-preview-04-2026`).

## 🛠️ Prerequisites

You will need Python 3.9+ and an active Gemini API Key. 

*Note: The Deep Research Agent operates on the Gemini Interactions API, which is currently in Public Beta.*

## 📦 Installation

1. **Clone the repository**

    git clone https://github.com/mmb78/gemini-deepresearch-explorer.git
    cd gemini-deepresearch-explorer

2. **Install dependencies**

    pip install streamlit google-genai

3. **Set your API Key**
   Export your Gemini API key as an environment variable so the app can detect it securely:
   
   *Mac/Linux:*
    export GEMINI_API_KEY="your_api_key_here"

   *Windows (Command Prompt):*
    set GEMINI_API_KEY=your_api_key_here

   *Windows (PowerShell):*
    $env:GEMINI_API_KEY="your_api_key_here"

## 🚀 Usage

Start the Streamlit server:

    streamlit run app.py

The application will automatically open in your default web browser at http://localhost:8501.

### Recommended Workflow
1. **Configure:** Select your model tier and toggle the tools you need (e.g., Code Execution, Web Search) from the sidebar.
2. **Plan:** Ensure the sidebar is set to **Plan / Refine (Drafting)**. Ask the agent to outline a complex topic. Attach any necessary files (PDFs, images).
3. **Review:** Wait for the agent to output its proposed research outline and methodology.
4. **Execute:** If the plan looks good, switch the sidebar setting to **Execute (Final Report)**. Type "Go ahead with this plan" into the chat and hit enter.
5. **Monitor & Export:** Watch the live thoughts stream. Once the massive background task finishes, click 💾 **HTML** or 📄 **MD** in the sidebar to save a beautiful, shareable copy of your report.

## 🧩 Built-in Tools Supported
* **google_search:** Live web access to current information.
* **url_context:** Deep web page reading and content extraction.
* **code_execution:** Python data analysis, math processing, and chart generation.
* **file_search:** Local document, image, audio, and video reading via the Streamlit uploader to Google's file servers.
* **mcp_server:** Connect to your own internal enterprise APIs or local tools via comma-separated URLs.

## 📄 License
This project is open-source and available under the MIT License.