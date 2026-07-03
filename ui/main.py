# ui/main.py
import streamlit as st
import requests
import time
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# --- Page Config ---
st.set_page_config(page_title="ERA-Lite Research Dashboard", layout="wide", page_icon="🧬")

# --- Header ---
st.title("🧬 ERA-Lite Research Dashboard")
st.markdown("Autonomous Empirical Software Optimization")
st.markdown("---")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["📊 Experiment Workspace", "🚀 Submit DSA Problem", "📈 Submit ML Dataset"])

if 'selected_node_id' not in st.session_state:
    st.session_state.selected_node_id = None

# --- Experiment Workspace ---
if page == "📊 Experiment Workspace":
    try:
        res = requests.get(f"{API_URL}/api/experiments")
        if res.status_code == 200:
            experiments = res.json()["experiments"]
            if not experiments:
                st.info("No experiments run yet. Submit a problem to get started!")
            else:
                # Top Bar: Experiment Selector & Controls
                with st.container(border=True):
                    top_cols = st.columns([4, 1, 1, 1])
                    with top_cols[0]:
                        exp_options = [f"Exp #{exp['id']} | {exp['status']} | {exp['started_at'][:10]}" for exp in experiments]
                        selected_exp = st.selectbox("Select Experiment", exp_options, label_visibility="collapsed")
                        exp_id = int(selected_exp.split(" | ")[0].replace("Exp #", ""))
                    
                    with top_cols[1]:
                        if st.button("🛑 Cancel Run", use_container_width=True):
                            requests.post(f"{API_URL}/api/stop/{exp_id}")
                            st.success("Cancellation signal sent!")
                            time.sleep(1)
                            st.rerun()
                            
                    with top_cols[2]:
                        if st.button("🔄 Refresh", use_container_width=True):
                            st.rerun()

                    with top_cols[3]:
                        if st.button("🗑️ Delete", use_container_width=True):
                            requests.delete(f"{API_URL}/api/experiments/{exp_id}")
                            st.rerun()

                # Fetch Data
                res_exp = requests.get(f"{API_URL}/api/experiments/{exp_id}")
                if res_exp.status_code == 200:
                    data = res_exp.json()
                    details = data['details']

                    # Loading Screen
                    if details['status'] == 'RUNNING':
                        with st.spinner(f"⏳ Experiment {exp_id} is running. The workspace will load upon completion."):
                            time.sleep(10)
                            st.rerun()

                    # Global Metrics Bar
                    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                    m_col1.metric("Metric Target", details.get('metric', 'N/A'))
                    m_col2.metric("Nodes Explored", data['iterations'])
                    m_col3.metric("Best Score", f"{data['best_score']:.4f}")
                    m_col4.metric("Model Used", details.get('model', 'N/A'))
                    
                    st.markdown("---")
                    
                    # Main Workspace Layout (Left: Tree, Right: Tabs)
                    ws_col1, ws_col2 = st.columns([2, 3], gap="large")
                    
                    with ws_col1:
                        with st.container(border=True, height=650):
                            st.subheader("🌳 Search Tree Map")
                            st.caption("Blue edges = breakthroughs. 🏆 = Best Node. Click any node to inspect.")
                            res_tree = requests.get(f"{API_URL}/api/tree/{exp_id}")
                            if res_tree.status_code == 200:
                                tree_data = res_tree.json()['nodes']
                                best_score = data['best_score']
                                
                                nodes = []
                                edges = []
                                for n in tree_data:
                                    score = n['score']
                                    color = f"rgb({int(255*(1-score))}, {int(255*score)}, 50)"
                                    
                                    if score == best_score and score > 0:
                                        nodes.append(Node(
                                            id=n['id'], 
                                            label=f"🏆\n#{n['id']}\n{score:.2f}", 
                                            size=35, 
                                            color="#fbbf24", 
                                            shape="diamond", 
                                            font={'size': 16, 'color': '#000000', 'face': 'arial', 'bold': True}
                                        ))
                                    else:
                                        nodes.append(Node(
                                            id=n['id'], 
                                            label=f"#{n['id']}\n{score:.2f}", 
                                            size=25, 
                                            color=color, 
                                            font={'size': 14, 'color': '#000000', 'face': 'arial'}
                                        ))
                                    
                                    if n['parent_id']:
                                        parent_score = next((pn['score'] for pn in tree_data if pn['id'] == n['parent_id']), 0)
                                        if score > parent_score + 0.1:
                                            edges.append(Edge(source=n['parent_id'], target=n['id'], color="#3b82f6", width=3))
                                        else:
                                            edges.append(Edge(source=n['parent_id'], target=n['id'], color="#cbd5e1", width=1))
                                
                                config = Config(
                                    width=700, 
                                    height=550, 
                                    directed=True, 
                                    physics=True, 
                                    hierarchical=True, 
                                    nodeHighlightBehavior=True, 
                                    highlightColor="#3b82f6"
                                )
                                clicked_node = agraph(nodes=nodes, edges=edges, config=config)
                                
                                if clicked_node:
                                    st.session_state.selected_node_id = clicked_node
                            else:
                                st.warning("Tree data not available.")

                    with ws_col2:
                        tab1, tab2, tab3 = st.tabs(["📋 Overview", "🏆 Best Code", "🔍 Node Inspector"])
                        
                        with tab1:
                            with st.container(border=True):
                                st.markdown("#### Problem Statement")
                                st.info(details['problem'])
                                
                                if details.get('dataset_filename'):
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        st.markdown("**Dataset:**")
                                        st.code(details['dataset_filename'])
                                    with c2:
                                        st.markdown("**Metric:**")
                                        st.code(details.get('metric', 'N/A'))
                                        
                                    if details.get('dataset_preview'):
                                        st.markdown("**Data Preview (First 5 rows):**")
                                        st.code(details['dataset_preview'], language="text")
                                        
                            st.markdown("#### Iteration History")
                            st.dataframe(data['history'], width="stretch", height=250)
                        
                        with tab2:
                            with st.container(border=True):
                                st.markdown("#### Winning Solution")
                                if data['best_code']:
                                    clean_code = data['best_code'].strip()
                                    st.code(clean_code, language="python")
                                else:
                                    st.warning("No successful code found.")

                        with tab3:
                            if st.session_state.get('selected_node_id'):
                                node_id = st.session_state.selected_node_id
                                res_node = requests.get(f"{API_URL}/api/node/{node_id}")
                                if res_node.status_code == 200:
                                    node_data = res_node.json()
                                    
                                    with st.container(border=True):
                                        n_col1, n_col2 = st.columns(2)
                                        n_col1.metric("Node ID", node_id)
                                        n_col2.metric("Score", f"{node_data['score']:.4f}")
                                        
                                        if node_data.get('reasoning'):
                                            st.markdown("#### 🧠 AI Thought Process")
                                            st.info(node_data['reasoning'])
                                        
                                        node_code = node_data['code'].strip()
                                        st.markdown("**Generated Code:**")
                                        st.code(node_code, language="python")
                                        
                                        if node_data['stdout']:
                                            st.markdown("**Execution Output (stdout):**")
                                            st.code(node_data['stdout'], language="text")
                                            
                                        if node_data['stderr']:
                                            st.markdown("**Errors (stderr):**")
                                            st.code(node_data['stderr'], language="text")
                            else:
                                st.info("👆 Click a node in the tree map to inspect it here.")
                else:
                    st.error("Could not fetch experiment details.")
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to backend. Is `uvicorn api:app --reload` running?")

# --- DSA Submission ---
elif page == "🚀 Submit DSA Problem":
    st.header("Define Algorithmic Problem")
    
    with st.container(border=True):
        problem_desc = st.text_area("Problem Description (Include test cases & examples here)", height=300, placeholder="Given a linked list, swap every two adjacent nodes...\n\nExample 1:\nInput: head = [1,2,3,4]\nOutput: [2,1,4,3]")
        func_name = st.text_input("Function Name", value="solve")

    st.markdown("---")
    if st.button("🚀 Run DSA Experiment", type="primary"):
        if not problem_desc or not func_name:
            st.error("Please provide a problem description and function name.")
        else:
            payload = {"problem": problem_desc, "function_name": func_name}
            with st.spinner("Submitting to backend..."):
                try:
                    res = requests.post(f"{API_URL}/api/run", json=payload)
                    if res.status_code == 200:
                        st.success("Experiment started! Go to the Workspace to see the loading screen.")
                    else:
                        st.error(f"API Error: {res.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to FastAPI backend.")

# --- ML Dataset Submission ---
elif page == "📈 Submit ML Dataset":
    st.header("Dataset ML Mode (Kaggle Style)")
    st.markdown("Upload a CSV dataset and tell the AI what to optimize.")
    
    with st.container(border=True):
        ml_problem = st.text_area(
            "Problem Description (Plain English)", 
            height=100,
            placeholder="e.g., Predict the 'target' column. This is a binary classification problem."
        )
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            ml_metric = st.selectbox(
                "Metric to Maximize", 
                [
                    "Auto-Detect (AI decides based on data)", 
                    "accuracy", "f1_score", "roc_auc", 
                    "r2_score", "neg_mean_squared_error", "neg_root_mean_squared_error"
                ]
            )
        with col_m2:
            ml_iterations = st.slider("Max Iterations (Cost/Time Control)", min_value=2, max_value=15, value=5, step=1)
            st.caption(f"Total nodes explored = {ml_iterations * 3}")
        
        uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.markdown("#### Dataset Preview")
                st.dataframe(df.head(5), width="stretch")
                st.caption(f"Rows: {df.shape[0]} | Cols: {df.shape[1]} | The AI will see the first 5 rows to understand columns and data types.")
            except Exception as e:
                st.error(f"Could not read CSV: {e}")

    st.markdown("---")
    if st.button("🚀 Run ML Experiment", type="primary"):
        if not uploaded_file or not ml_problem:
            st.error("Please provide a problem description and upload a CSV.")
        else:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            # FIX: Explicitly cast iteration to string to ensure it sends correctly in Form data
            data = {"problem": ml_problem, "metric": ml_metric, "iterations": str(ml_iterations)}
            
            with st.spinner("Uploading dataset and starting ML agents..."):
                try:
                    res = requests.post(f"{API_URL}/api/run_dataset", files=files, data=data)
                    if res.status_code == 200:
                        st.success("ML Experiment started! Go to the Workspace to see the loading screen.")
                    else:
                        st.error(f"API Error: {res.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to FastAPI backend.")