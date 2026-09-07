from langchain_core.tools import tool


def make_tools(db, user_id):
    from models import Assignation, Complaint, User, UserRole

    signed_in_user = db.get(User, user_id)

    @tool
    def search_knowledge_base(query: str) -> str:
        """Search CMS guides and complaint records."""
        from ai.knowledge_base import build_knowledge_base
        store = build_knowledge_base(db)
        if not store:
            return "AI knowledge search is unavailable without an OpenAI key."
        return "\n\n".join(item.page_content for item in store.similarity_search(query, k=4))

    @tool
    def get_current_user_context() -> str:
        """Return the signed-in user's username, role, and available permissions."""
        if not signed_in_user:
            return "No user is signed in."
        permissions = {
            UserRole.CUSTOMER: "create complaints and view own complaints",
            UserRole.EMPLOYEE: "create complaints, view assigned complaints, and update assigned complaint status",
            UserRole.ADMIN: "create complaints, list users, assign any complaint, change any status, and view reports",
        }[signed_in_user.role]
        return f"Signed in as {signed_in_user.username} ({signed_in_user.role.value}). Permissions: {permissions}."

    @tool
    def get_complaint_by_id(complaint_id: int) -> str:
        """Look up one complaint by ID."""
        from models import Complaint
        item = db.get(Complaint, complaint_id)
        return f"#{item.id}: {item.title} | {item.status.value} | {item.description}" if item else "Complaint not found."

    @tool
    def list_my_complaints() -> str:
        """List complaints belonging to the signed-in customer."""
        from services.complaint_service import list_complaints
        return "\n".join(f"#{item.id} {item.title}: {item.status.value}" for item in list_complaints(db, user_id)) or "No complaints found."

    @tool
    def create_complaint(title: str, description: str, priority: str = "Medium") -> str:
        """Create a new complaint for the signed-in customer. Use only after the user gives a title and description."""
        if not signed_in_user:
            return "You must be signed in to create a complaint."
        from services.complaint_service import create_complaint as save_complaint
        complaint = save_complaint(db, title, description, priority.title(), user_id)
        destination = "My complaints" if signed_in_user.role == UserRole.CUSTOMER else "Assigned complaints" if signed_in_user.role == UserRole.EMPLOYEE else "Admin|Complaints"
        return f"Complaint #{complaint.id} created successfully. [ACTION:navigate:{destination}]"

    @tool
    def list_assigned_complaints() -> str:
        """Show complaints assigned to the signed-in employee."""
        if not signed_in_user or signed_in_user.role != UserRole.EMPLOYEE:
            return "Only employees have assigned task lists."
        assignments = db.query(Assignation).filter(Assignation.employee_id == user_id).all()
        if not assignments:
            return "No complaints are assigned to you."
        lines = [f"#{item.complaint.id} {item.complaint.title} | {item.complaint.status.value} | {item.complaint.priority}" for item in assignments]
        return "Your assigned complaints:\n" + "\n".join(lines) + " [ACTION:navigate:Assigned complaints]"

    @tool
    def update_my_assigned_complaint_status(complaint_id: int, status: str) -> str:
        """Employee action: update a complaint status only when it is assigned to the signed-in employee."""
        if not signed_in_user or signed_in_user.role != UserRole.EMPLOYEE:
            return "Only employees can update assigned complaint status."
        assignment = db.query(Assignation).filter(Assignation.complaint_id == complaint_id, Assignation.employee_id == user_id).first()
        if not assignment:
            return f"Complaint #{complaint_id} is not assigned to you."
        from services.complaint_service import update_status
        normalized_status = status.strip().upper().replace(" ", "_")
        if normalized_status == "INPROGRESS":
            normalized_status = "IN_PROGRESS"
        complaint = update_status(db, complaint_id, normalized_status)
        return f"Assigned complaint #{complaint.id} status changed to {complaint.status.value}. [ACTION:navigate:Assigned complaints]"

    @tool
    def list_all_users() -> str:
        """List CMS users for the signed-in administrator."""
        if not signed_in_user or signed_in_user.role != UserRole.ADMIN:
            return "Only administrators can list all users."
        users = "\n".join(f"{item.username} ({item.role.value}) - {item.email}" for item in db.query(User).order_by(User.username))
        return users + " [ACTION:navigate:Admin|Users]"

    @tool
    def assign_complaint_to_employee(complaint_id: int, employee_username: str, status: str = "OPEN") -> str:
        """Admin action: assign any complaint to an employee and optionally set its status."""
        if not signed_in_user or signed_in_user.role != UserRole.ADMIN:
            return "Only administrators can assign complaints."
        employee = db.query(User).filter(User.username == employee_username, User.role == UserRole.EMPLOYEE).first()
        complaint = db.get(Complaint, complaint_id)
        if not employee:
            return f"Employee {employee_username} was not found."
        if not complaint:
            return f"Complaint #{complaint_id} was not found."
        from services.assignation_service import assign_complaint
        from services.complaint_service import update_status
        assign_complaint(db, complaint.id, employee.id, notes="Assigned by admin assistant")
        update_status(db, complaint.id, status.upper().replace(" ", "_"))
        return f"Complaint #{complaint.id} assigned to {employee.username} with status {status.upper()}. [ACTION:navigate:Admin|Assign]"

    @tool
    def change_complaint_status(complaint_id: int, status: str) -> str:
        """Admin action: change any complaint status to OPEN, IN_PROGRESS, RESOLVED, or CLOSED."""
        if not signed_in_user or signed_in_user.role != UserRole.ADMIN:
            return "Only administrators can override complaint status."
        from services.complaint_service import update_status
        complaint = update_status(db, complaint_id, status.upper().replace(" ", "_"))
        if not complaint:
            return f"Complaint #{complaint_id} was not found."
        return f"Complaint #{complaint.id} status changed to {complaint.status.value}. [ACTION:navigate:Admin|Assign]"

    @tool
    def report_complaints(employee_username: str = "ALL", status: str = "ALL") -> str:
        """Admin report: list complaints filtered by assigned employee and status, then open the filtered report view."""
        if not signed_in_user or signed_in_user.role != UserRole.ADMIN:
            return "Only administrators can run employee complaint reports."
        from models import ComplaintStatus
        employee_username = employee_username.strip().lower().replace(" ", "")
        normalized_status = status.strip().upper().replace(" ", "_")
        if normalized_status == "PENDING":
            normalized_status = "OPEN"
        if normalized_status == "INPROGRESS":
            normalized_status = "IN_PROGRESS"
        valid_statuses = {item.value for item in ComplaintStatus}
        if normalized_status != "ALL" and normalized_status not in valid_statuses:
            return "Use status OPEN, IN_PROGRESS, RESOLVED, CLOSED, or ALL."
        results = db.query(Complaint).all()
        if employee_username != "all":
            results = [item for item in results if item.assignments and item.assignments[-1].employee.username == employee_username]
        if normalized_status != "ALL":
            results = [item for item in results if item.status.value == normalized_status]
        lines = [f"#{item.id} {item.title} | {item.status.value} | {item.assignments[-1].employee.username if item.assignments else 'Unassigned'}" for item in results]
        body = "\n".join(lines) if lines else "No complaints match those filters."
        return body + f" [ACTION:report:{employee_username}|{normalized_status}]"

    @tool
    def open_page(page: str) -> str:
        """Request navigation to a CMS page."""
        normalized_page = page.lower().strip()
        if normalized_page in {"administration", "admin dashboard", "admin"}:
            return "Opening Admin. [ACTION:navigate:Admin|Complaints]"
        if "report" in normalized_page:
            return "Opening Reports. [ACTION:navigate:Reports]"
        if "user" in normalized_page:
            return "Opening users. [ACTION:navigate:Admin|Users]"
        if "assign" in normalized_page:
            return "Opening assignment. [ACTION:navigate:Admin|Assign]"
        if "complaint" in normalized_page:
            return "Opening complaints. [ACTION:navigate:Admin|Complaints]"
        return f"Opening {page}. [ACTION:navigate:{page}]"

    return [search_knowledge_base, get_current_user_context, get_complaint_by_id, list_my_complaints, create_complaint, list_assigned_complaints, update_my_assigned_complaint_status, list_all_users, assign_complaint_to_employee, change_complaint_status, report_complaints, open_page]
