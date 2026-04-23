import streamlit as st
import os
import time
import base64
import json
import warnings
from google import genai

# ==========================================
# 🛑 Suppress Beta SDK Terminal Warnings
# ==========================================
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="pydantic")

# ==========================================
# ⚙️ APP CONFIGURATION
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY", "")

AVAILABLE_MODELS = {
    "Preview (Faster)": "deep-research-preview-04-2026",
    "Max (Comprehensive)": "deep-research-max-preview-04-2026"
}

DEFAULT_TOOLS = ["google_search", "url_context", "code_execution"]

# ==========================================
# Export & Helper Functions
# ==========================================
def get_raw_dict(obj):
    try:
        return json.loads(obj.model_dump_json())
    except:
        try:
            return obj.to_dict()
        except:
            return {"raw_string_fallback": str(obj)}

def truncate_b64_for_ui(data):
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k == 'data' and isinstance(v, str) and len(v) > 500:
                new_dict[k] = v[:50] + "... [BASE64 TRUNCATED] ..."
            else:
                new_dict[k] = truncate_b64_for_ui(v)
        return new_dict
    elif isinstance(data, list):
        return [truncate_b64_for_ui(i) for i in data]
    else:
        return data

def parse_recovered_input(api_input):
    """Recursively digs through the SDK's Turn/Content objects to extract pure text."""
    if not api_input:
        return ""
    if isinstance(api_input, str):
        return api_input
    
    texts = []
    if isinstance(api_input, list):
        for item in api_input:
            text = parse_recovered_input(item)
            if text: texts.append(text)
        return "\n\n".join(texts)
        
    if hasattr(api_input, "content"):
        return parse_recovered_input(api_input.content)
    if hasattr(api_input, "parts"):
        return parse_recovered_input(api_input.parts)
    if hasattr(api_input, "text") and api_input.text:
        return api_input.text
    if isinstance(api_input, dict) and "text" in api_input:
        return api_input["text"]
        
    return ""

def process_recovered_interaction(interaction):
    """Converts a single API interaction object into our UI message format."""
    messages_to_add = []
    
    # 1. Recover the User Prompt
    if getattr(interaction, 'input', None):
        extracted_input = parse_recovered_input(interaction.input)
        if extracted_input:
            messages_to_add.append({
                "role": "user", 
                "blocks": [{"type": "text", "content": f"*(Recovered Prompt)*\n\n{extracted_input}"}]
            })

    # 2. Recover the Assistant Response (Parent ID First, then Current ID)
    prev_id = getattr(interaction, 'previous_interaction_id', None)
    
    header_text = ""
    if prev_id:
        header_text += f"🔗 **Parent Session ID:** `{prev_id}`\n\n"
    header_text += f"✅ **Current Turn ID:** `{interaction.id}`"
    
    resume_msg = {
        "role": "assistant", 
        "blocks": [{"type": "text", "content": header_text}],
        "raw_json": get_raw_dict(interaction)
    }
    
    if hasattr(interaction, 'outputs') and interaction.outputs:
        for o in interaction.outputs:
            if o.type == "text" and o.text:
                clean_text = o.text.replace("\n", "  \n")
                resume_msg["blocks"].append({"type": "text", "content": clean_text})
            elif o.type == "image" and o.data:
                img_bytes = base64.b64decode(o.data)
                resume_msg["blocks"].append({"type": "image", "content": img_bytes})

    messages_to_add.append(resume_msg)
    return messages_to_add

def generate_html_export(messages):
    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Deep Research Export</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #333; }
        .user { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0066cc; }
        .assistant { margin: 20px 0; }
        img { max-width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 15px 0; }
        pre { background: #f1f5f9; padding: 15px; border-radius: 8px; overflow-x: auto; }
        code { background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-family: monospace; }
        table { border-collapse: collapse; width: 100%; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f8f9fa; }
    </style>
</head>
<body>
    <h1>🕵️‍♂️ Deep Research Report</h1>
    <hr>
    <div id="content"></div>
    <script>
"""
    export_data = []
    for msg in messages:
        msg_dict = {"role": msg["role"], "blocks": []}
        for block in msg["blocks"]:
            if block["type"] == "text":
                msg_dict["blocks"].append({"type": "text", "content": block["content"]})
            elif block["type"] == "image":
                b64_str = base64.b64encode(block["content"]).decode("utf-8")
                msg_dict["blocks"].append({"type": "image", "content": b64_str})
        export_data.append(msg_dict)
        
    json_data = json.dumps(export_data)
    html_template += f"""
        const sessionData = {json_data};
        const contentDiv = document.getElementById('content');
        sessionData.forEach(msg => {{
            const div = document.createElement('div');
            if (msg.role === 'user') {{
                div.className = 'user';
                div.innerHTML = '<strong>👤 User:</strong><br>';
                msg.blocks.forEach(b => {{ if(b.type === 'text') div.innerHTML += marked.parse(b.content); }});
            }} else {{
                div.className = 'assistant';
                div.innerHTML = '<strong>🤖 Assistant:</strong><br>';
                msg.blocks.forEach(b => {{
                    if (b.type === 'text') {{
                        div.innerHTML += marked.parse(b.content);
                    }} else if (b.type === 'image') {{
                        div.innerHTML += '<img src="data:image/png;base64,' + b.content + '" /><br>';
                    }}
                }});
                div.innerHTML += '<hr>';
            }}
            contentDiv.appendChild(div);
        }});
    </script>
</body>
</html>"""
    return html_template

def generate_md_export(messages):
    md_text = "# 🕵️‍♂️ Deep Research Report\n\n"
    for msg in messages:
        role_icon = "👤 User" if msg["role"] == "user" else "🤖 Assistant"
        md_text += f"### {role_icon}\n"
        for block in msg["blocks"]:
            if block["type"] == "text":
                md_text += f"{block['content']}\n\n"
            elif block["type"] == "image":
                b64_str = base64.b64encode(block["content"]).decode("utf-8")
                md_text += f"![Visualization](data:image/png;base64,{b64_str})\n\n"
        md_text += "---\n\n"
    return md_text

# ==========================================
# Page Configuration & API Setup
# ==========================================
st.set_page_config(page_title="Gemini Deep Research", page_icon="🕵️‍♂️", layout="wide")

if not API_KEY:
    st.error("⚠️ No API Key found. Please set `API_KEY` at the top of the script or use the `GEMINI_API_KEY` environment variable.")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ==========================================
# Session State Management
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "interaction_id" not in st.session_state:
    st.session_state.interaction_id = None
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# ==========================================
# Sidebar Settings
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='margin-top: -10px; margin-bottom: 5px;'>🕵️‍♂️ Gemini Deep Research</h3>", unsafe_allow_html=True)
    
    # --- RESUME SESSION ---
    st.markdown("**Resume Session**")
    resume_id = st.text_input("Resume Session ID:", placeholder="Paste Interaction ID...", label_visibility="collapsed")
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        recover_single = st.button("Recover Last Turn", use_container_width=True)
    with col_res2:
        recover_full = st.button("Recover Full Chat", use_container_width=True)
    
    if recover_single and resume_id:
        try:
            with st.spinner("Fetching past interaction..."):
                past_interaction = client.interactions.get(id=resume_id.strip(), include_input=True)
                st.session_state.interaction_id = past_interaction.id
                
                new_msgs = process_recovered_interaction(past_interaction)
                st.session_state.messages.extend(new_msgs)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to resume: {e}")

    if recover_full and resume_id:
        try:
            with st.spinner("Tracing conversation history..."):
                history_chain = []
                current_id = resume_id.strip()
                
                while current_id:
                    interaction = client.interactions.get(id=current_id, include_input=True)
                    history_chain.append(interaction)
                    current_id = getattr(interaction, 'previous_interaction_id', None)
                
                history_chain.reverse()
                st.session_state.interaction_id = history_chain[-1].id
                
                for step in history_chain:
                    new_msgs = process_recovered_interaction(step)
                    st.session_state.messages.extend(new_msgs)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to resume full chain: {e}")

    # --- MODEL TIER ---
    st.markdown("<br>**Model Tier**", unsafe_allow_html=True)
    model_name = st.selectbox("Select Agent Model:", list(AVAILABLE_MODELS.keys()), label_visibility="collapsed")
    agent_id = AVAILABLE_MODELS[model_name]
    
    # --- AGENT CONFIGURATION ---
    st.markdown("**Agent Configuration**")
    enable_thinking = st.toggle("Thinking Summaries", value=True)
    enable_visuals = st.toggle("Visualization", value=True)
    
    # --- TOOLS ---
    st.markdown("**Tools**")
    selected_tools = st.multiselect(
        "Select enabled tools:",
        ["google_search", "url_context", "code_execution", "file_search"],
        default=DEFAULT_TOOLS,
        label_visibility="collapsed"
    )
    
    tool_configs = [{"type": t} for t in selected_tools]
    
    mcp_servers = st.text_input("MCP Servers:", placeholder="http://localhost:8080...")
    if mcp_servers:
        tool_configs.append({"type": "mcp_server", "servers": [s.strip() for s in mcp_servers.split(",")]})

    if "file_search" in selected_tools:
        uploaded_file = st.file_uploader("Upload Context File:", accept_multiple_files=False)
        if uploaded_file and st.button("Upload to Gemini", use_container_width=True):
            with st.spinner("Uploading..."):
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                gemini_file = client.files.upload(file=temp_path)
                st.session_state.uploaded_files.append(gemini_file.name)
                os.remove(temp_path)
                st.success(f"Uploaded: {gemini_file.name}")
    
    # --- WORKFLOW PHASE ---
    st.markdown("**Workflow Phase**")
    workflow_mode = st.radio(
        "Next Action:",
        ["Plan / Refine (Drafting)", "Execute (Final Report)"],
        label_visibility="collapsed"
    )
    is_planning = (workflow_mode == "Plan / Refine (Drafting)")

    # --- EXPORT ---
    st.markdown("<br>**Export Session**", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(label="💾 HTML", data=generate_html_export(st.session_state.messages), file_name="deep_research_report.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button(label="📄 MD", data=generate_md_export(st.session_state.messages), file_name="deep_research_report.md", mime="text/markdown", use_container_width=True)
    
    # --- RESET ---
    st.markdown("<br>", unsafe_allow_html=True) 
    if st.button("🗑️ Reset Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.interaction_id = None
        st.rerun()

# ==========================================
# Main Chat Interface
# ==========================================
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        for block in msg["blocks"]:
            if block["type"] == "text":
                st.markdown(block["content"])
            elif block["type"] == "image":
                st.image(block["content"])
        
        # 🟢 FIX: Place JSON Save and View side-by-side using columns
        if msg.get("raw_json"):
            st.markdown("<br>", unsafe_allow_html=True)
            # Give the expander more space (4) and the button less (1)
            col_json1, col_json2 = st.columns([1, 4]) 
            
            with col_json1:
                dl_key = f"dl_json_{idx}"
                json_str = json.dumps(msg["raw_json"], indent=2)
                st.download_button(
                    label="📦 Save JSON",
                    data=json_str,
                    file_name=f"interaction_turn_{idx}.json",
                    mime="application/json",
                    key=dl_key,
                    use_container_width=True
                )
                
            with col_json2:
                with st.expander("🛠️ View JSON"):
                    ui_safe_json = truncate_b64_for_ui(msg["raw_json"])
                    st.json(ui_safe_json)

if prompt := st.chat_input("Enter your research topic or feedback..."):
    
    st.session_state.messages.append({"role": "user", "blocks": [{"type": "text", "content": prompt}]})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_container = st.status(f"Starting task with **{model_name}**...", expanded=True)
        
        id_placeholder = status_container.empty()
        thought_placeholder = status_container.empty()
        
        try:
            agent_config = {
                "type": "deep-research",
                "thinking_summaries": "auto" if enable_thinking else "none",
                "collaborative_planning": is_planning,
                "visualization": "auto" if enable_visuals else "none"
            }
            
            interaction_kwargs = {
                "agent": agent_id,
                "input": prompt,
                "agent_config": agent_config,
                "tools": tool_configs,
                "background": True,
                "stream": True 
            }
            
            if st.session_state.interaction_id:
                interaction_kwargs["previous_interaction_id"] = st.session_state.interaction_id
                
            stream = client.interactions.create(**interaction_kwargs)
            
            stream_state = {
                "interaction_id": None,
                "last_event_id": None,
                "is_complete": False,
                "live_thoughts": "",
                "live_text": ""
            }
            
            outputs = {}

            def process_stream(current_stream):
                for chunk in current_stream:
                    if chunk.event_type == "interaction.start":
                        stream_state["interaction_id"] = chunk.interaction.id
                        st.session_state.interaction_id = stream_state["interaction_id"]
                        id_placeholder.markdown(f"✅ **Task Started!** ID: `{stream_state['interaction_id']}`")
                    
                    if chunk.event_id:
                        stream_state["last_event_id"] = chunk.event_id
                    
                    if chunk.event_type == "content.start":
                        outputs[chunk.index] = {"type": chunk.content.type}
                    
                    elif chunk.event_type == "content.delta":
                        output = outputs[chunk.index]
                        if chunk.delta.type == "text":
                            output["text"] = output.get("text", "") + chunk.delta.text
                            stream_state["live_text"] = output["text"] 
                        elif chunk.delta.type == "thought_summary":
                            new_thought = getattr(chunk.delta.content, "text", "")
                            output["summary"] = output.get("summary", "") + new_thought
                            stream_state["live_thoughts"] += new_thought
                            thought_placeholder.markdown(f"🤔 *{stream_state['live_thoughts'].replace(chr(10), '  '+chr(10))}*")

                    elif chunk.event_type in ("interaction.complete", "error"):
                        stream_state["is_complete"] = True

            process_stream(stream)

            while not stream_state["is_complete"] and stream_state["interaction_id"]:
                status = client.interactions.get(stream_state["interaction_id"])
                if status.status != "in_progress":
                    break
                
                status_container.write("🔄 *Reconnecting stream...*")
                resume_stream = client.interactions.get(
                    id=stream_state["interaction_id"], 
                    stream=True, 
                    last_event_id=stream_state["last_event_id"]
                )
                process_stream(resume_stream)

            status_container.update(label="Research Complete!", state="complete", expanded=False)
            
            final_interaction = client.interactions.get(id=stream_state["interaction_id"])
            final_json = get_raw_dict(final_interaction)
            
            final_blocks = []
            if final_interaction.outputs:
                for o in final_interaction.outputs:
                    if o.type == "text" and o.text:
                        clean_text = o.text.replace("\n", "  \n")
                        final_blocks.append({"type": "text", "content": clean_text})
                    elif o.type == "image" and o.data:
                        final_blocks.append({"type": "image", "content": base64.b64decode(o.data)})

            for block in final_blocks:
                if block["type"] == "text":
                    st.markdown(block["content"])
                elif block["type"] == "image":
                    st.image(block["content"])
            
            st.session_state.messages.append({
                "role": "assistant", 
                "blocks": final_blocks,
                "raw_json": final_json
            })
            
            st.rerun()
            
        except Exception as e:
            status_container.update(label="An error occurred", state="error")
            st.error(f"API Error: {str(e)}")