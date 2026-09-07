import streamlit as st
from sqlalchemy import select

from db import session_scope
from models import Assignation, ComplaintStatus
from services.complaint_service import create_complaint
from services.complaint_service import update_status


def render(user):
    st.header("Assigned complaints")
    with st.expander("Create complaint", expanded=False):
        with st.form("employee_new_complaint"):
            title = st.text_input("Title", key="employee_complaint_title")
            description = st.text_area("Description", key="employee_complaint_description")
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"], key="employee_complaint_priority")
            if st.form_submit_button("Create complaint"):
                if title and description:
                    with session_scope() as create_db:
                        complaint = create_complaint(create_db, title, description, priority, user["id"])
                    st.success(f"Complaint #{complaint.id} created.")
                else:
                    st.error("Title and description are required.")
    with session_scope() as db:
        assignments = list(db.scalars(select(Assignation).where(Assignation.employee_id == user["id"])))
        for assignment in assignments:
            complaint = assignment.complaint
            with st.container(border=True):
                st.subheader(f"#{complaint.id} {complaint.title}")
                st.write(complaint.description)
                status = st.selectbox("Status", [item.value for item in ComplaintStatus], index=[item.value for item in ComplaintStatus].index(complaint.status.value), key=f"status_{complaint.id}")
                notes = st.text_area("Internal notes", value=assignment.notes or "", key=f"notes_{assignment.id}")
                if st.button("Save update", key=f"save_{assignment.id}"):
                    update_status(db, complaint.id, status)
                    assignment.notes = notes
                    db.commit()
                    st.success("Complaint updated.")
