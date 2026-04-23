# 🕵️‍♂️ Gemini DeepResearch Explorer

An interactive, Streamlit-based graphical interface for Google's **Gemini Deep Research API**. 

This application transforms the powerful, asynchronous Gemini Interactions API into a sleek conversational workspace. It allows you to collaboratively plan massive research tasks, watch the agent's "thoughts" stream in real-time, recover past sessions, and export your final reports (complete with inline charts and graphs) into portable formats.

## ✨ Features

* **Collaborative Planning:** Don't just prompt and pray. Ask the agent to generate a research outline, refine it conversationally, and then pull the trigger on full execution.
* **Live Thought Streaming:** Watch the agent's internal monologue in real-time as it searches the web, reads documents, and synthesizes data.
* **Session Recovery:** Close your browser, come back tomorrow, and paste your Interaction ID to seamlessly resume a multi-hour research task or recover your entire chat history.
* **Local File Context:** Upload local PDFs or text files directly into the UI to allow the agent to read your private documents alongside public web data.
* **Rich Exports:** Download your final reports as styled HTML (with embedded images), Markdown, or raw JSON for debugging.
* **Model Toggling:** Easily switch between the lightning-fast Preview model for drafting and the comprehensive Max model for heavy-duty execution.

## 🛠️ Prerequisites

You will need Python 3.9+ and an active Gemini API Key. 

*Note: The Deep Research Agent operates on the new Gemini Interactions API, which is currently in Public Beta.*

## 📦 Installation

1. **Clone the repository**

   git clone [https://github.com/mmb78/gemini-deepresearch-explorer.git](https://github.com/mmb78/gemini-deepresearch-explorer.git)
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
1. **Plan:** Ensure the sidebar is set to Plan / Refine (Drafting). Ask the agent to research a complex topic.
2. **Review:** Wait for the agent to output its proposed research outline.
3. **Execute:** If the plan looks good, switch the sidebar setting to Execute (Final Report). Type "Go ahead" into the chat and hit enter.
4. **Export:** Once the massive background task finishes, click 💾 HTML in the sidebar to save a beautiful, shareable copy of your report.

## 🧩 Built-in Tools Supported
* google_search: Live web access (Enabled by default)
* url_context: Deep web page reading (Enabled by default)
* code_execution: Python data analysis (Enabled by default)
* file_search: Local document reading via UI uploader
* mcp_server: Connect to your own internal enterprise APIs

## 📄 License
This project is open-source and available under the MIT License.
