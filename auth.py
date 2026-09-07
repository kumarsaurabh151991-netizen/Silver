import secrets

import bcrypt
import streamlit as st
from sqlalchemy import or_, select

from db import session_scope
from models import User, UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def current_user() -> User | None:
    return st.session_state.get("user")


def login(username: str, password: str) -> bool:
    with session_scope() as db:
        user = db.scalar(select(User).where(User.username == username.strip()))
        if user and verify_password(password, user.password_hash):
            st.query_params.clear()
            st.session_state.pop("agent_page", None)
            st.session_state.pop("agent_tab", None)
            st.session_state.user = {"id": user.id, "username": user.username, "role": user.role.value, "email": user.email}
            return True
    return False


def auth_page() -> None:
    st.title("Complaint Management System")
    mode = st.tabs(["Sign in", "Register", "Reset password"])
    with mode[0]:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in", type="primary"):
                if login(username, password):
                    st.rerun()
                st.error("Invalid username or password")
    with mode[1]:
        with st.form("register"):
            username = st.text_input("Username", key="reg_username")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            if st.form_submit_button("Create account"):
                with session_scope() as db:
                    exists = db.scalar(select(User).where(or_(User.username == username, User.email == email)))
                    if exists or not username or not email or len(password) < 6:
                        st.error("Choose a unique username/email and a password of at least 6 characters.")
                    else:
                        db.add(User(username=username, email=email, password_hash=hash_password(password)))
                        db.commit()
                        st.success("Account created. You can sign in now.")
    with mode[2]:
        st.info("For this local demo, reset tokens are shown on screen rather than emailed.")
        email = st.text_input("Account email", key="reset_email")
        if st.button("Create reset token"):
            with session_scope() as db:
                user = db.scalar(select(User).where(User.email == email))
                if user:
                    st.session_state.reset_token = secrets.token_urlsafe(12)
                    st.session_state.reset_user_id = user.id
            if st.session_state.get("reset_token"):
                st.code(st.session_state.reset_token)
            else:
                st.error("No account found.")
        token = st.text_input("Reset token", key="reset_token_input")
        new_password = st.text_input("New password", type="password", key="new_password")
        if st.button("Reset password"):
            if token and token == st.session_state.get("reset_token") and len(new_password) >= 6:
                with session_scope() as db:
                    user = db.get(User, st.session_state.reset_user_id)
                    user.password_hash = hash_password(new_password)
                    db.commit()
                st.success("Password reset. Sign in with your new password.")
            else:
                st.error("Use a valid token and a password of at least 6 characters.")
