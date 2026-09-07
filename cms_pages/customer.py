import streamlit as st

from db import session_scope
from services.complaint_service import create_complaint, list_complaints


def render(user):
    st.header("My complaints")
    with st.expander("Create complaint", expanded=True):
        with st.form("new_complaint"):
            title = st.text_input("Title")
            description = st.text_area("What happened?")
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
            if st.form_submit_button("Create complaint", type="primary"):
                if title and description:
                    with session_scope() as db:
                        complaint = create_complaint(db, title, description, priority, user["id"])
                    st.success(f"Complaint #{complaint.id} submitted.")
                else:
                    st.error("Title and description are required.")
    with session_scope() as db:
        complaints = list_complaints(db, user["id"])
        for complaint in complaints:
            with st.container(border=True):
                st.subheader(f"#{complaint.id} {complaint.title}")
                st.write(complaint.description)
                st.write(f"Status: **{complaint.status.value}** · Priority: **{complaint.priority}**")
