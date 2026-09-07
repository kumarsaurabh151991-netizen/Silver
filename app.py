import streamlit as st
from sqlalchemy import select

from ai.startup_info import print_startup_info
from auth import auth_page
from components.floating_chat import render as floating_chat
from db import init_db, session_scope
from models import Assignation, Complaint, User, UserRole


def sync_page_selection():
    st.query_params["page"] = st.session_state.cms_navigation


def seed_data():
    from auth import hash_password
    init_db()
    with session_scope() as db:
        accounts = [
            ("admin", "admin@cms.local", "admin123", UserRole.ADMIN),
            ("customer", "customer@cms.local", "customer123", UserRole.CUSTOMER),
            ("customer2", "customer2@cms.local", "customer123", UserRole.CUSTOMER),
            ("customer3", "customer3@cms.local", "customer123", UserRole.CUSTOMER),
            ("employee", "employee@cms.local", "employee123", UserRole.EMPLOYEE),
            ("employee2", "employee2@cms.local", "employee123", UserRole.EMPLOYEE),
            ("employee3", "employee3@cms.local", "employee123", UserRole.EMPLOYEE),
        ]
        users = {}
        for username, email, password, role in accounts:
            user = db.scalar(select(User).where(User.username == username))
            if not user:
                user = User(username=username, email=email, password_hash=hash_password(password), role=role)
                db.add(user)
                db.flush()
            users[username] = user

        complaint_data = [
            ("Streetlight outage", "The streetlight outside building 4 is not working.", "Medium", "customer"),
            ("Water pressure issue", "Low water pressure since yesterday.", "High", "customer"),
            ("Billing statement question", "The latest utility statement contains an unexpected charge.", "Low", "customer2"),
            ("Broken park bench", "A bench in Central Park has a damaged seat and is unsafe.", "Medium", "customer2"),
            ("Missed waste collection", "Waste collection was missed twice this week.", "Urgent", "customer3"),
            ("Noise complaint", "Construction work is continuing outside the permitted hours.", "High", "customer3"),
        ]
        complaints = []
        for title, description, priority, owner in complaint_data:
            complaint = db.scalar(select(Complaint).where(Complaint.title == title))
            if not complaint:
                complaint = Complaint(title=title, description=description, priority=priority, created_by=users[owner].id)
                db.add(complaint)
                db.flush()
            complaints.append(complaint)

        for complaint, employee_name in zip(complaints, ["employee", "employee", "employee2", "employee2", "employee3", "employee3"]):
            assigned = db.scalar(select(Assignation).where(Assignation.complaint_id == complaint.id))
            if not assigned:
                db.add(Assignation(complaint_id=complaint.id, employee_id=users[employee_name].id, notes="Seeded demo assignment"))
        db.commit()


st.set_page_config(page_title="CMS-APPLICATION-PY", page_icon="C", layout="wide")
st.markdown("""
<style>
    [data-testid="stSidebar"] { min-width: 360px; max-width: 360px; }
    [data-testid="stSidebarContent"] { padding-left: 1rem; padding-right: 1rem; }
</style>
""", unsafe_allow_html=True)
print_startup_info()
seed_data()

if "user" not in st.session_state:
    st.session_state.user = None
if not st.session_state.user:
    with st.sidebar:
        st.caption("Menu")
        st.radio("", ["Sign in", "Register", "Forgot password"], label_visibility="collapsed", disabled=True)
        floating_chat(0)
    auth_page()
else:
    user = st.session_state.user
    with st.sidebar:
        st.title("CMS")
        st.caption(f"Signed in as {user['username']} · {user['role']}")
        options = ["My complaints"] if user["role"] == "CUSTOMER" else ["Assigned complaints"] if user["role"] == "EMPLOYEE" else ["Admin", "Reports"]
        requested_page = st.session_state.pop("agent_page", None) or st.query_params.get("page")
        selected_page = requested_page if requested_page in options else options[0]
        st.session_state["cms_navigation"] = selected_page
        page = st.radio("Navigate", options, key="cms_navigation", on_change=sync_page_selection)
        if st.button("Sign out"):
            st.session_state.user = None
            st.query_params.clear()
            st.session_state.pop("cms_navigation", None)
            st.session_state.pop("admin_section", None)
            st.rerun()
        floating_chat(user["id"])
    if page == "My complaints":
        from cms_pages.customer import render
    elif page == "Assigned complaints":
        from cms_pages.employee import render
    elif page == "Admin":
        from cms_pages.admin import render
    elif page == "Reports":
        from cms_pages.reports import render
    render(user)
