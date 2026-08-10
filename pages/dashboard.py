# dashboard.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import json
from collections import Counter
import pandas as pd
import plotly.graph_objects as go
from run_pipeline import analyze_repository

# ---------------------- Constants ----------------------
HISTORY_FILE = "search_history.json"

# ---------------------- Utility Functions ----------------------
def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:5], f)

def load_issues(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def count_labels(issues, key):
    values = [issue.get(key, "unknown") for issue in issues]
    return Counter(values)

def clean_action(action):
    return action.split(":")[-1].strip().lower()

def render_bar_chart(data_dict, title):
    theme = st.get_option("theme.base")
    is_dark = theme == "dark"
    color = "#3fb950" if is_dark else "#2f81f7"

    fig = go.Figure(data=[go.Bar(x=list(data_dict.keys()), y=list(data_dict.values()), marker_color=color)])
    fig.update_layout(
        title=title,
        xaxis_title="Labels",
        yaxis_title="Count",
        template="plotly_dark" if is_dark else "plotly_white",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

def get_github_url(issue):
    """Extract GitHub URL from issue data with proper fallbacks"""
    # Try html_url first (this is the proper GitHub web URL)
    if issue.get("html_url"):
        return issue["html_url"]
    # Fallback to url if html_url doesn't exist
    elif issue.get("url"):
        return issue["url"]
    # Last resort - construct URL if we have number and repo info
    elif issue.get("number"):
        # This would need repo info - might need to be passed from context
        return f"https://github.com/{st.session_state.repo_input}/issues/{issue['number']}"
    else:
        return "#"

def create_github_link_button(issue):
    """Create a working GitHub link button"""
    github_url = get_github_url(issue)
    
    # Use st.link_button if available (Streamlit 1.29+), otherwise use markdown
    try:
        st.link_button("🌐 View on GitHub", github_url, use_container_width=False)
    except AttributeError:
        # Fallback for older Streamlit versions
        st.markdown(f'<a href="{github_url}" target="_blank" rel="noopener noreferrer" style="'
                   'display: inline-block; '
                   'background-color: #238636; '
                   'color: white; '
                   'padding: 8px 16px; '
                   'border-radius: 6px; '
                   'text-decoration: none; '
                   'font-weight: bold; '
                   'font-size: 14px; '
                   'margin: 4px 0;">🌐 View on GitHub</a>', 
                   unsafe_allow_html=True)

# ---------------------- Session Setup ----------------------
if "search_history" not in st.session_state:
    st.session_state.search_history = load_history()

if "repo_input" not in st.session_state:
    st.session_state.repo_input = ""

# Handle jump from main.py
if st.session_state.get("jump_to_dashboard"):
    repo_input = st.session_state.get("last_repo")
    del st.session_state["jump_to_dashboard"]
    st.session_state.repo_input = repo_input
    if repo_input not in st.session_state.search_history:
        st.session_state.search_history.insert(0, repo_input)
        save_history(st.session_state.search_history)
    st.rerun()

# ---------------------- Streamlit Config ----------------------
st.set_page_config(page_title="DevRel Insights", layout="wide")

# ---------------------- GitHub Theme Styling ----------------------
st.markdown("""<style>
/* Example GitHub-like dark card styling */
.github-card {
    background-color: #161b22;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    border: 1px solid #30363d;
}

/* Ensure links open in new tab */
.github-link {
    display: inline-block;
    background-color: #238636;
    color: white !important;
    padding: 8px 16px;
    border-radius: 6px;
    text-decoration: none;
    font-weight: bold;
    font-size: 14px;
    margin: 4px 0;
    transition: background-color 0.2s;
}

.github-link:hover {
    background-color: #2ea043;
    color: white !important;
}
</style>""", unsafe_allow_html=True)

# ---------------------- Title ----------------------
st.title("🤖 DevRel Insights Dashboard")
st.markdown("Powered by your LLM agents")

# ---------------------- Sidebar ----------------------
st.sidebar.markdown("## 🔎 Analyze a GitHub Repository")

# Manual input for new repo
repo_input = st.sidebar.text_input("Enter repo (format: owner/repo)", value=st.session_state.repo_input, key="repo_manual_input")

if st.sidebar.button("🚀 Run Analysis", key="analyze_new_repo"):
    with st.spinner("Analyzing repository..."):
        try:
            analyze_repository(repo_input)
            st.session_state.repo_input = repo_input
            if repo_input not in st.session_state.search_history:
                st.session_state.search_history.insert(0, repo_input)
                save_history(st.session_state.search_history)
            st.success("✅ Analysis complete! Reloading...")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")

# History buttons
st.sidebar.markdown("### 🕘 Recent Repositories")
for i, repo in enumerate(st.session_state.search_history):
    if st.sidebar.button(f"🔁 {repo}", key=f"history_btn_{i}"):
        st.session_state.repo_input = repo
        st.rerun()

if st.sidebar.button("🧹 Clear History"):
    st.session_state.search_history = []
    save_history([])
    st.rerun()

# ---------------------- Load Data ----------------------
repo_key = st.session_state.repo_input.replace("/", "_")
json_path = f"data/{repo_key}_devrel.json"

try:
    issues = load_issues(json_path)
    st.success(f"✅ Loaded {len(issues)} issues from `{st.session_state.repo_input}`")
except FileNotFoundError:
    st.error(f"❌ No processed file found for {st.session_state.repo_input}. Please run analysis first.")
    st.stop()

# ---------------------- Filters ----------------------

# Label filtering
unique_labels = sorted(set(issue.get("predicted_label", "unknown") for issue in issues))
selected_label = st.selectbox("🎯 Filter by predicted label:", ["All"] + unique_labels)
filtered_issues = (
    [i for i in issues if i.get("predicted_label") == selected_label]
    if selected_label != "All" else issues
)

# Search filtering
search_query = st.text_input("🔍 Search issues by title/body text", "", key="search_box")
if search_query:
    filtered_issues = [
        i for i in filtered_issues
        if search_query.lower() in i.get("title", "").lower() or search_query.lower() in i.get("body", "").lower()
    ]
    st.info(f"🔎 Found {len(filtered_issues)} issue(s) matching: `{search_query}`")

# ---------------------- Charts ----------------------
st.markdown("### 📊 Compare Model vs GitHub Labels")
if st.toggle("Show bar charts", value=True, key="show_charts"):
    st.subheader("🤖 Predicted Labels")
    render_bar_chart(count_labels(filtered_issues, "predicted_label"), "Predicted Labels")

    st.subheader("🏷️ GitHub Labels")
    all_labels = []
    for issue in filtered_issues:
        for label in issue.get("labels", []):
            if isinstance(label, dict):
                # Label is an object with a 'name' field
                label_name = label.get("name", "").lower()
            elif isinstance(label, str):
                # Label is already a string
                label_name = label.lower()
            else:
                # Unknown label format
                label_name = str(label).lower()
            
            if label_name:  # Only add non-empty labels
                all_labels.append(label_name)
    
    render_bar_chart(Counter(all_labels), "GitHub Labels")

# ---------------------- Export Buttons ----------------------
st.markdown("### 📥 Export Filtered Issues")

# JSON
st.download_button(
    "📄 Download JSON",
    json.dumps(filtered_issues, indent=2),
    file_name="filtered_issues.json"
)

# Markdown
st.download_button(
    "📝 Download Markdown",
    "\n\n".join(
        f"### #{i['number']} - {i['title']}\n\n{i.get('body', '')[:500]}...\n\n**Predicted:** {i.get('predicted_label')} | **DevRel:** {i.get('devrel_action', '-')}"
        for i in filtered_issues
    ),
    file_name="filtered_issues.md"
)

# CSV
df = pd.DataFrame(filtered_issues)
st.download_button("📊 Download CSV", df.to_csv(index=False), file_name="filtered_issues.csv")

# ---------------------- DevRel Suggestions ----------------------
top_actions = Counter(clean_action(i.get("devrel_action", "")) for i in filtered_issues if i.get("devrel_action"))
if top_actions:
    with st.expander("💡 Top DevRel Suggestions (Click to expand)", expanded=True):
        for action, count in top_actions.most_common(5):
            st.markdown(f"- **{action.capitalize()}** ({count})")
else:
    st.warning("❌ No DevRel suggestions found in the current filtered results.")

# ---------------------- Misclassified Issues ----------------------
# Fix: Compare with label names, not the full label objects
misclassified = []
for issue in filtered_issues:
    predicted = issue.get("predicted_label", "").lower()
    github_labels = []
    
    # Handle both string and object labels
    for label in issue.get("labels", []):
        if isinstance(label, dict):
            label_name = label.get("name", "").lower()
        elif isinstance(label, str):
            label_name = label.lower()
        else:
            label_name = str(label).lower()
        
        if label_name:
            github_labels.append(label_name)
    
    if predicted not in github_labels and predicted != "unknown":
        misclassified.append(issue)

if misclassified:
    with st.expander(f"⚠️ {len(misclassified)} Potentially Misclassified Issues", expanded=False):
        show_all = st.checkbox("🔍 Show all", value=False, key="show_all_misclass")
        to_show = misclassified if show_all else misclassified[:5]
        for issue in to_show:
            st.markdown(f"**#{issue['number']} — {issue['title']}**")
            
            # Handle both string and object labels
            github_label_names = []
            for label in issue.get("labels", []):
                if isinstance(label, dict):
                    github_label_names.append(label.get("name", ""))
                elif isinstance(label, str):
                    github_label_names.append(label)
                else:
                    github_label_names.append(str(label))
            
            st.markdown(f"🔸 _Predicted:_ `{issue.get('predicted_label')}` | _GitHub:_ `{', '.join(github_label_names) or 'None'}`")
            st.markdown("---")
else:
    st.info("✅ No misclassified issues found.")

# ---------------------- Sample 'Question' Issues ----------------------
st.markdown("---")
st.subheader("❓ Sample 'Question' Issues")
q_issues = [i for i in filtered_issues if i.get("predicted_label") == "question"]
if not q_issues:
    st.info("No issues labeled as 'question'.")
else:
    for issue in q_issues[:3]:
        with st.container():
            st.markdown("<div class='github-card'>", unsafe_allow_html=True)
            
            # Title and GitHub link
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**#{issue['number']}** — {issue['title']}")
            with col2:
                create_github_link_button(issue)
            
            st.code(issue.get("body", "")[:250] + "...", language="markdown")

            # DevRel Suggestion Tag
            devrel = issue.get("devrel_action", "").strip()
            st.markdown("💡 **LLM Suggestion:**")
            if devrel:
                st.markdown(
                    f"<div style='display:inline-block; background-color:#238636; color:white; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>{devrel}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='display:inline-block; background-color:#444; color:white; padding:4px 10px; border-radius:12px; font-size:12px;'>No suggestion</div>",
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- Full Viewer ----------------------
st.markdown("---")
st.subheader("📚 All Issues (Full Details)")
if st.toggle("🔽 Show all issues with full context", key="show_full_context"):
    for issue in filtered_issues:
        with st.container():
            st.markdown("<div class='github-card'>", unsafe_allow_html=True)
            
            # Title and GitHub link
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**#{issue['number']}** — {issue['title']}")
            with col2:
                create_github_link_button(issue)
            
            st.write(issue.get("body", ""))
            st.markdown(f"🗓️ Created: `{issue.get('created_at', 'N/A')}`")

            # DevRel Tag
            devrel = issue.get("devrel_action", "").strip()
            st.markdown("💡 **LLM Suggestion:**")
            if devrel:
                st.markdown(
                    f"<div style='display:inline-block; background-color:#238636; color:white; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>{devrel}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='display:inline-block; background-color:#444; color:white; padding:4px 10px; border-radius:12px; font-size:12px;'>No suggestion</div>",
                    unsafe_allow_html=True
                )

            if (ctx := issue.get("web_context", "").strip()):
                with st.expander("🌐 Web Context (Tavily Snippets)"):
                    import re
                    def format_links(text):
                        return re.sub(
                            r"🔗 (https?://\S+)",
                            r"🔗 <a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
                            text
                        )
                    formatted_ctx = format_links(ctx)
                    st.markdown(formatted_ctx, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

# ---------------------- Recent Issues ----------------------
st.subheader("🆕 Latest 5 Issues")
try:
    recent_issues = sorted(filtered_issues, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
    for issue in recent_issues:
        with st.container():
            st.markdown("<div class='github-card'>", unsafe_allow_html=True)
            
            # Title and GitHub link
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**#{issue['number']}** — {issue['title']}")
            with col2:
                create_github_link_button(issue)
            
            st.write(issue.get("body", "")[:500] + "...")

            # DevRel Tag
            devrel = issue.get("devrel_action", "").strip()
            st.markdown("💡 **LLM Suggestion:**")
            if devrel:
                st.markdown(
                    f"<div style='display:inline-block; background-color:#238636; color:white; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600;'>{devrel}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<div style='display:inline-block; background-color:#444; color:white; padding:4px 10px; border-radius:12px; font-size:12px;'>No suggestion</div>",
                    unsafe_allow_html=True
                )

            if (ctx := issue.get("web_context", "").strip()):
                with st.expander("🌐 Web Context (Tavily Snippets)"):
                    import re
                    def format_links(text):
                        return re.sub(
                            r"🔗 (https?://\S+)",
                            r"🔗 <a href='\1' target='_blank' rel='noopener noreferrer'>\1</a>",
                            text
                        )
                    formatted_ctx = format_links(ctx)
                    st.markdown(formatted_ctx, unsafe_allow_html=True) 

            st.markdown("</div>", unsafe_allow_html=True)
except Exception:
    st.warning("⚠️ Could not sort by created_at. Make sure your data includes that field in ISO format.")