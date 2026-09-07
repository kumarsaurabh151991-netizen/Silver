import streamlit as st
from sqlalchemy import select

from db import session_scope
from models import Complaint, ComplaintStatus, UserRole
from services.assignation_service import assign_complaint
from services.complaint_service import create_complaint, update_status
from services.user_service import create_user, list_users


def sync_admin_section():
    st.query_params["page"] = "Admin"
    st.query_params["tab"] = st.session_state.admin_section


def complaint_rows(complaints):
    return [{
        "ID": item.id,
        "Title": item.title,
        "Priority": item.priority,
        "Status": item.status.value,
        "Submitted by": item.creator.username,
        "Assigned to": item.assignments[-1].employee.username if item.assignments else "-",
        "Created": item.created_at.strftime("%Y-%m-%d"),
        "Updated": item.updated_at.strftime("%Y-%m-%d"),
    } for item in complaints]


def render(user):
    st.header("Admin dashboard")
    with st.expander("Create complaint", expanded=False):
        with st.form("admin_new_complaint"):
            title = st.text_input("Title", key="admin_complaint_title")
            description = st.text_area("Description", key="admin_complaint_description")
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"], key="admin_complaint_priority")
            if st.form_submit_button("Create complaint"):
                if title and description:
                    with session_scope() as create_db:
                        complaint = create_complaint(create_db, title, description, priority, user["id"])
                    st.success(f"Complaint #{complaint.id} created.")
                else:
                    st.error("Title and description are required.")
    requested_tab = st.session_state.pop("agent_tab", None) or st.query_params.get("tab", "Complaints")
    sections = ["Complaints", "Assign", "Users"]
    selected_section = requested_tab if requested_tab in sections else sections[0]
    st.session_state["admin_section"] = selected_section
    section = st.radio("Admin section", sections, key="admin_section", on_change=sync_admin_section, horizontal=True, label_visibility="collapsed")
    with session_scope() as db:
        complaints = list(db.scalars(select(Complaint).order_by(Complaint.id.desc())))
        users = list_users(db)
        employees = [item for item in users if item.role == UserRole.EMPLOYEE]

        if section == "Complaints":
            status_filter = st.selectbox("Status filter", ["ALL"] + [item.value for item in ComplaintStatus])
            visible = complaints if status_filter == "ALL" else [item for item in complaints if item.status.value == status_filter]
            st.dataframe(complaint_rows(visible), use_container_width=True, hide_index=True)
            if complaints:
                st.subheader("Delete a complaint")
                selected = st.selectbox("Complaint", complaints, format_func=lambda item: f"#{item.id} - {item.title}")
                if st.button("Delete", type="secondary"):
                    db.delete(selected)
                    db.commit()
                    st.success(f"Complaint #{selected.id} deleted.")
                    st.rerun()

        elif section == "Assign":
            st.subheader("Assign and update complaints")
            if complaints and employees:
                task_col, employee_col, status_col = st.columns([2, 2, 2])
                with task_col:
                    selected_task = st.selectbox("Task", complaints, format_func=lambda item: f"#{item.id} - {item.title}")
                with employee_col:
                    selected_employee = st.selectbox("Employee", employees, format_func=lambda item: item.username)
                with status_col:
                    selected_status = st.selectbox("Status", [item.value for item in ComplaintStatus], index=[item.value for item in ComplaintStatus].index(selected_task.status.value))
                if st.button("Apply assignment", type="primary"):
                    assign_complaint(db, selected_task.id, selected_employee.id)
                    update_status(db, selected_task.id, selected_status)
                    st.success(f"Task #{selected_task.id} assigned to {selected_employee.username}.")
            else:
                st.info("Create at least one complaint and employee before assigning tasks.")

        else:
            st.subheader("Users")
            st.dataframe([{ "username": item.username, "email": item.email, "role": item.role.value } for item in users], use_container_width=True, hide_index=True)
            with st.expander("Add employee"):
                with st.form("add_employee"):
                    username = st.text_input("Username", key="employee_username")
                    email = st.text_input("Email", key="employee_email")
                    if st.form_submit_button("Create employee") and username and email:
                        create_user(db, username, email)
                        st.success("Employee created with password welcome123.")
