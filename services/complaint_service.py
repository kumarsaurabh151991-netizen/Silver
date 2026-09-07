from sqlalchemy import select

from db import utcnow
from models import Complaint, ComplaintStatus


def list_complaints(db, user_id=None):
    query = select(Complaint).order_by(Complaint.created_at.desc())
    if user_id:
        query = query.where(Complaint.created_by == user_id)
    return list(db.scalars(query))


def create_complaint(db, title, description, priority, user_id):
    complaint = Complaint(title=title, description=description, priority=priority, created_by=user_id)
    db.add(complaint)
    db.commit()
    return complaint


def update_status(db, complaint_id, status):
    complaint = db.get(Complaint, complaint_id)
    if complaint:
        complaint.status = ComplaintStatus(status)
        complaint.updated_at = utcnow()
        db.commit()
    return complaint
