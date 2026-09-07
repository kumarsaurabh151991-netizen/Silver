import re

import streamlit as st

from ai.agent_service import stream_agent
from db import session_scope


ACTION_PATTERN = re.compile(r"\[ACTION:navigate:([^\]]+)\]")
REPORT_PATTERN = re.compile(r"\[ACTION:report:([^|\]]+)\|([^\]]+)\]")


def _navigate_from_response(response: str) -> str:
    report_action = REPORT_PATTERN.search(response)
    if report_action:
        st.session_state["agent_page"] = "Reports"
        st.query_params["page"] = "Reports"
        st.query_params["report_tab"] = "By user"
        st.query_params["report_employee"] = report_action.group(1)
        st.query_params["report_status"] = report_action.group(2)
        response = REPORT_PATTERN.sub("", response).strip()
    action = ACTION_PATTERN.search(response)
    if not action:
        return response
    for key in list(st.session_state):
        if key.startswith("status_") or key.startswith("admin_status_"):
            del st.session_state[key]
    destination = action.group(1).split("|", 1)
    st.session_state["agent_page"] = destination[0]
    st.session_state["agent_tab"] = destination[1] if len(destination) == 2 else ""
    st.query_params["page"] = destination[0]
    if len(destination) == 2:
        st.query_params["tab"] = destination[1]
    else:
        st.query_params.pop("tab", None)
    return ACTION_PATTERN.sub("", response).strip()


def render(user_id: int):
    st.markdown("### CMS Assistant")
    st.caption("Ask me to create, find, assign, or navigate CMS tasks.")
    history_key = f"assistant_messages_{user_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    with st.container(height=360, border=True):
        for message in st.session_state[history_key][-8:]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        live_messages = st.empty()

    prompt = st.chat_input("Ask about complaints or users", key=f"assistant_input_{user_id}")
    if not prompt:
        return

    st.session_state[history_key].append({"role": "user", "content": prompt})
    with live_messages.container():
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            try:
                with session_scope() as db:
                    response = st.write_stream(stream_agent(prompt, db, user_id))
            except Exception as error:
                response = "The assistant could not complete that request. Use the CMS controls on this page to continue manually."
                st.warning(response)
    response = _navigate_from_response(response)
    st.session_state[history_key].append({"role": "assistant", "content": response})
    st.rerun()
