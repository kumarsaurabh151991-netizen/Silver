from sqlalchemy import select

from auth import hash_password
from models import User, UserRole


def list_users(db):
    return list(db.scalars(select(User).order_by(User.username)))


def create_user(db, username, email, role=UserRole.EMPLOYEE, password="welcome123"):
    user = User(username=username, email=email, role=role, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user
