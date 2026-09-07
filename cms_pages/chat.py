import streamlit as st

from ai.agent_service import stream_agent
from db import session_scope


def render(user):
    st.header("AI Assistant")
    st.caption("Ask about the CMS guide or your complaint status.")
    for item in st.session_state.get("chat_history", []):
        with st.chat_message(item["role"]):
            st.write(item["content"])
    if prompt := st.chat_input("Ask the assistant"):
        st.session_state.chat_history = st.session_state.get("chat_history", []) + [{"role": "user", "content": prompt}]
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with session_scope() as db:
                response = st.write_stream(stream_agent(prompt, db, user["id"]))
        st.session_state.chat_history.append({"role": "assistant", "content": response})
