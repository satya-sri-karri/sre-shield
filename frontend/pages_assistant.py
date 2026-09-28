import streamlit as st
import asyncio
from backend.agents.assistant import assistant_agent

def show_assistant_page():
    st.markdown("## 🤖 SRE AI Copilot & Memory Assistant")
    st.markdown("Ask natural-language questions about past outages, effective runbooks, and cluster failure modes grounded in Hindsight Incident Memory.")
    st.write("")

    # Quick Question Chips
    st.markdown("##### 💡 Suggested Questions (Grounded in Historical Incidents):")
    q_col1, q_col2 = st.columns(2)
    with q_col1:
        if st.button("💬 What happened the last time Checkout API failed with 500?", use_container_width=True):
            st.session_state["user_chat_input"] = "What happened the last time Checkout API failed with 500?"
        if st.button("💬 Which runbook worked for database connection failures?", use_container_width=True):
            st.session_state["user_chat_input"] = "Which runbook worked for database connection failures?"
    with q_col2:
        if st.button("💬 What was the root cause of the previous Redis incident?", use_container_width=True):
            st.session_state["user_chat_input"] = "What was the root cause of the previous Redis incident?"
        if st.button("💬 Why did Inventory Service pod crash with exit code 137?", use_container_width=True):
            st.session_state["user_chat_input"] = "Why did Inventory Service pod crash with exit code 137?"

    st.write("---")

    # Chat history state
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": "Hello Engineer! I am SRE-Shield Copilot. I have persistent memory of all past production incidents, post-mortems, and runbook executions. How can I assist you with cluster reliability today?"
            }
        ]

    # Render previous messages
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User chat input
    user_prompt = st.chat_input("Ask about past incidents, runbooks, or error root causes...")
    
    # If button set input
    if "user_chat_input" in st.session_state and st.session_state["user_chat_input"]:
        user_prompt = st.session_state.pop("user_chat_input")

    if user_prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching Hindsight 4-Network Memory & synthesizing response..."):
                response_data = asyncio.run(assistant_agent.ask(user_prompt))
                answer = response_data.get("answer", "No response generated.")
                st.markdown(answer)

                top_m = response_data.get("top_match")
                if top_m:
                    st.caption(f"📌 Grounded in Hindsight Memory: `{top_m['id']}` (Incident `{top_m['incident_id']}` on `{top_m['service']}`)")

        st.session_state["chat_messages"].append({"role": "assistant", "content": answer})
