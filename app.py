import streamlit as st
import os
import time
import base64
import json
import warnings
import zipfile
import io
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
    if not api_input: return ""
    if isinstance(api_input, str): return api_input
    
    texts = []
    if isinstance(api_input, list):
        for item in api_input:
            text = parse_recovered_input(item)
            if text: texts.append(text)
        return "\n\n".join(texts)
        
    if hasattr(api_input, "content"): return parse_recovered_input(api_input.content)
    if hasattr(api_input, "parts"): return parse_recovered_input(api_input.parts)
    if hasattr(api_input, "text") and api_input.text: return api_input.text
    if isinstance(api_input, dict) and "text" in api_input: return api_input["text"]
        
    return ""

def process_recovered_interaction(interaction):
    messages_to_add = []
    
    # 1. User Prompt
    if getattr(interaction, 'input', None):
        extracted_input = parse_recovered_input(interaction.input)
        if extracted_input:
            messages_to_add.append({
                "role": "user", 
                "blocks": [{"type": "text", "content": f"*(Recovered Prompt)*\n\n{extracted_input}"}]
            })

    # 2. Reconstruct ID and Thoughts Header
    prev_id = getattr(interaction, 'previous_interaction_id', None)
    header_text = ""
    if prev_id: header_text += f"🔗 **Parent Session ID:** `{prev_id}`\n\n"
    header_text += f"✅ **Turn ID:** `{interaction.id}`\n\n"
    
    thoughts = ""
    if hasattr(interaction, 'outputs') and interaction.outputs:
        for o in interaction.outputs:
            if o.type == "thought" and getattr(o, "summary", None):
                parsed_thought = parse_recovered_input(o.summary)
                if parsed_thought: thoughts += f"{parsed_thought}\n"
    
    if thoughts:
        clean_thoughts = thoughts.strip().replace(chr(10), chr(10)+'> ')
        header_text += f"🤔 **Thinking:**\n> {clean_thoughts}\n\n---\n\n"
    
    resume_msg = {
        "role": "assistant", 
        "blocks": [{"type": "text", "content": header_text}],
        "raw_json": get_raw_dict(interaction)
    }
    
    # 3. Reconstruct Text and Images
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
                try:
                    # FIX: Safe base64 encoding fallback for exports
                    b64_str = base64.b64encode(block["content"]).decode("utf-8")
                    msg_dict["blocks"].append({"type": "image", "content": b64_str})
                except Exception:
                    msg_dict["blocks"].append({"type": "text", "content": "[Image Corrupted/Unexportable]"})
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
                try:
                    # FIX: Safe base64 encoding fallback for exports
                    b64_str = base64.b64encode(block["content"]).decode("utf-8")
                    md_text += f"![Visualization](data:image/png;base64,{b64_str})\n\n"
                except Exception:
                    md_text += f"*[Image Corrupted/Unexportable]*\n\n"
        md_text += "---\n\n"
    return md_text
    
def generate_json_zip(messages):
    zip_buffer = io.BytesIO()
    json_count = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, msg in enumerate(messages):
            if msg.get("raw_json"):
                interaction_id = msg['raw_json'].get('id', 'unknown')
                json_str = json.dumps(msg["raw_json"], indent=2)
                zip_file.writestr(f"turn_{i}_id_{interaction_id}.json", json_str)
                json_count += 1
    if json_count == 0:
        return None
    return zip_buffer.getvalue()

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
if "messages" not in st.session_state: st.session_state.messages = []
if "interaction_id" not in st.session_state: st.session_state.interaction_id = None
if "uploaded_files" not in st.session_state: st.session_state.uploaded_files = []

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
    st.markdown("**Enabled Tools**")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        use_search = st.checkbox("Web Search", value=True)
        use_code = st.checkbox("Code Exec", value=True)
    with col_t2:
        use_url = st.checkbox("URL Reader", value=True)
        use_mcp = st.checkbox("MCP Server", value=False)
        
    tool_configs = []
    if use_search: tool_configs.append({"type": "google_search"})
    if use_code: tool_configs.append({"type": "code_execution"})
    if use_url: tool_configs.append({"type": "url_context"})
    
    if use_mcp:
        mcp_servers = st.text_input("MCP Server URLs (comma separated):", placeholder="http://localhost:8080")
        if mcp_servers:
            tool_configs.append({"type": "mcp_server", "servers": [s.strip() for s in mcp_servers.split(",")]})

    # --- FILE UPLOADER ---
    st.markdown("<br>**Attach Documents/Images**", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload File:", accept_multiple_files=False, label_visibility="collapsed")
    if uploaded_file and st.button("Attach to Session", use_container_width=True):
        with st.spinner("Uploading and processing file on Google servers..."):
            temp_path = f"temp_{uploaded_file.name}"
            # FIX: Ensure safe file cleanup even if API fails
            try:
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                gemini_file = client.files.upload(file=temp_path, config={'display_name': uploaded_file.name})
                
                while True:
                    file_info = client.files.get(name=gemini_file.name)
                    if file_info.state == "ACTIVE": 
                        st.session_state.uploaded_files.append({"name": uploaded_file.name, "file_obj": file_info})
                        st.success(f"Successfully Attached: {uploaded_file.name}")
                        break
                    elif file_info.state == "FAILED":
                        st.error("File processing failed on Google's end.")
                        break
                    time.sleep(2)
            except Exception as e:
                st.error(f"Upload error: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
    if st.session_state.uploaded_files:
        st.markdown("*Files ready to send with next prompt:*")
        for f in st.session_state.uploaded_files:
            st.caption(f"📎 {f['name']}")
        if st.button("Clear Attachments", use_container_width=True):
            st.session_state.uploaded_files = []
            st.rerun()
    
    # --- WORKFLOW PHASE ---
    st.markdown("<br>**Workflow Phase**", unsafe_allow_html=True)
    workflow_mode = st.radio("Next Action:", ["Plan / Refine (Drafting)", "Execute (Final Report)"], label_visibility="collapsed")
    is_planning = (workflow_mode == "Plan / Refine (Drafting)")

    # --- EXPORT ---
    st.markdown("<br>**Export Session**", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(label="💾 HTML", data=generate_html_export(st.session_state.messages), file_name="deep_research_report.html", mime="text/html", use_container_width=True)
    with col2:
        st.download_button(label="📄 MD", data=generate_md_export(st.session_state.messages), file_name="deep_research_report.md", mime="text/markdown", use_container_width=True)
    with col3:
        zip_data = generate_json_zip(st.session_state.messages)
        st.download_button(label="📦 ZIP", data=zip_data if zip_data else b"", file_name="deep_research_jsons.zip", mime="application/zip", use_container_width=True, disabled=(zip_data is None))
    
    # --- RESET ---
    st.markdown("<br>", unsafe_allow_html=True) 
    if st.button("🗑️ Reset Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.interaction_id = None
        st.session_state.uploaded_files = []
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
        
        if msg.get("raw_json"):
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Token usage stats block
            usage = msg["raw_json"].get("usage", {})
            if usage:
                st.caption(f"📊 **Tokens** | In: `{usage.get('total_input_tokens', 0)}` | Out: `{usage.get('total_output_tokens', 0)}` | Thought: `{usage.get('total_thought_tokens', 0)}` | Total: `{usage.get('total_tokens', 0)}`")
            
            col_json1, col_json2 = st.columns([1, 4]) 
            with col_json1:
                dl_key = f"dl_json_{idx}"
                json_str = json.dumps(msg["raw_json"], indent=2)
                st.download_button(
                    label="📦 Save JSON", data=json_str, file_name=f"interaction_turn_{idx}.json",
                    mime="application/json", key=dl_key, use_container_width=True
                )
            with col_json2:
                with st.expander("🛠️ View JSON"):
                    ui_safe_json = truncate_b64_for_ui(msg["raw_json"])
                    st.json(ui_safe_json)

if prompt := st.chat_input("Enter your research topic or feedback..."):
    
    user_blocks = [{"type": "text", "content": prompt}]
    if st.session_state.uploaded_files:
        file_names = ", ".join([f["name"] for f in st.session_state.uploaded_files])
        user_blocks.insert(0, {"type": "text", "content": f"📎 *Attached files: {file_names}*\n"})
        
    st.session_state.messages.append({"role": "user", "blocks": user_blocks})
    
    with st.chat_message("user"):
        for b in user_blocks:
            st.markdown(b["content"])

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
                "agent_config": agent_config,
                "tools": tool_configs,
                "background": True,
                "stream": True 
            }
            
            if st.session_state.uploaded_files:
                multimodal_input = []
                for f_data in st.session_state.uploaded_files:
                    f_obj = f_data["file_obj"]
                    mime = getattr(f_obj, 'mime_type', 'application/pdf')
                    
                    if mime.startswith("image/"): f_type = "image"
                    elif mime.startswith("audio/"): f_type = "audio"
                    elif mime.startswith("video/"): f_type = "video"
                    else: f_type = "document"
                    
                    multimodal_input.append({"type": f_type, "uri": f_obj.uri, "mime_type": mime})
                
                multimodal_input.append({"type": "text", "text": prompt})
                interaction_kwargs["input"] = multimodal_input
            else:
                interaction_kwargs["input"] = prompt
            
            if st.session_state.interaction_id:
                interaction_kwargs["previous_interaction_id"] = st.session_state.interaction_id
                
            stream = client.interactions.create(**interaction_kwargs)
            
            # FIX: Clear attachments only after stream creation succeeds
            st.session_state.uploaded_files = [] 
            
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

            # FIX: Added try/except and time.sleep to avoid API spam if the connection drops
            while not stream_state["is_complete"] and stream_state["interaction_id"]:
                status = client.interactions.get(stream_state["interaction_id"])
                if status.status != "in_progress":
                    break
                status_container.write("🔄 *Reconnecting stream...*")
                
                try:
                    resume_stream = client.interactions.get(
                        id=stream_state["interaction_id"], stream=True, last_event_id=stream_state["last_event_id"]
                    )
                    process_stream(resume_stream)
                except Exception as e:
                    status_container.write(f"⚠️ *Reconnect failed, retrying... ({e})*")
                
                time.sleep(2)

            status_container.update(label="Research Complete!", state="complete", expanded=False)
            
            final_interaction = client.interactions.get(id=stream_state["interaction_id"])
            final_json = get_raw_dict(final_interaction)
            
            final_blocks = []
            header_text = f"✅ **Turn ID:** `{stream_state['interaction_id']}`\n\n"
            if stream_state["live_thoughts"]:
                clean_live_thoughts = stream_state['live_thoughts'].strip().replace(chr(10), chr(10)+'> ')
                header_text += f"🤔 **Thinking:**\n> {clean_live_thoughts}\n\n---\n\n"
            final_blocks.append({"type": "text", "content": header_text})
            
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