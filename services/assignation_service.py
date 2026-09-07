from sqlalchemy import select

from models import Assignation


def assign_complaint(db, complaint_id, employee_id, notes=""):
    assignment = Assignation(complaint_id=complaint_id, employee_id=employee_id, notes=notes)
    db.add(assignment)
    db.commit()
    return assignment


def assignments_for_employee(db, employee_id):
    return list(db.scalars(select(Assignation).where(Assignation.employee_id == employee_id)))
