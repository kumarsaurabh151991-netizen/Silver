import re

from ai.availability import is_available
from config import CHAT_MODEL


def _status_value(value):
    from models import ComplaintStatus
    normalized = value.strip().upper().replace(" ", "_")
    aliases = {"PENDING": "OPEN", "INPROGRESS": "IN_PROGRESS", "IN_PROGRESS": "IN_PROGRESS"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {item.value for item in ComplaintStatus} else None


def _employee_name(value):
    compact = value.strip().lower().replace(" ", "")
    if compact.startswith("employee") and compact[8:].isdigit():
        return compact
    return value.strip().lower()


def _local_command(message, db, user_id):
    """Handle common CMS actions even when OpenAI is unavailable."""
    normalized = message.lower().strip()
    from models import User, UserRole
    user = db.get(User, user_id)

    if user and user.role == UserRole.ADMIN and "report" in normalized and ("employee" in normalized or "status" in normalized):
        employee_match = re.search(r"employee\s*(\d+)", normalized)
        status_match = re.search(r"(open|pending|in\s*progress|resolved|closed)", normalized)
        employee_name = _employee_name(f"employee{employee_match.group(1)}") if employee_match else "ALL"
        status = _status_value(status_match.group(1)) if status_match else "ALL"
        from models import Assignation, Complaint
        results = db.query(Complaint).all()
        if employee_name != "ALL":
            results = [item for item in results if item.assignments and item.assignments[-1].employee.username == employee_name]
        if status != "ALL":
            results = [item for item in results if item.status.value == status]
        lines = [f"#{item.id} {item.title} | {item.status.value} | {item.assignments[-1].employee.username if item.assignments else 'Unassigned'}" for item in results]
        return ("Matching reports:\n" + "\n".join(lines) if lines else "No complaints match those report filters.") + f" [ACTION:report:{employee_name}|{status}]"

    if user and user.role == UserRole.ADMIN:
        assign_match = re.search(r"assign (?:the )?(?:complaint|task)(?: id)?\s*#?(\d+)\s+to\s+(employee\s*\d+|[a-zA-Z0-9_.-]+)(?:\s+(?:with\s+)?status\s+([a-zA-Z_ ]+))?", normalized)
        if assign_match:
            complaint_id = int(assign_match.group(1))
            employee_username = _employee_name(assign_match.group(2))
            chained_status = re.search(r"(?:status|set|mark)(?:\s+it)?\s+(?:to\s+)?(open|pending|in\s*progress|resolved|closed)", normalized)
            status = _status_value(assign_match.group(3) or (chained_status.group(1) if chained_status else "OPEN"))
            from services.assignation_service import assign_complaint
            from services.complaint_service import update_status
            from models import Assignation, Complaint
            complaint = db.get(Complaint, complaint_id)
            employee = db.query(User).filter(User.username == employee_username, User.role == UserRole.EMPLOYEE).first()
            if not complaint:
                return f"Complaint #{complaint_id} was not found."
            if not employee:
                return f"Employee {employee_username} was not found."
            assign_complaint(db, complaint.id, employee.id, notes="Assigned by admin assistant")
            if not status:
                return "Use a valid status: OPEN, IN_PROGRESS, RESOLVED, or CLOSED."
            update_status(db, complaint.id, status)
            return f"Complaint #{complaint.id} assigned to {employee.username} with status {status}. [ACTION:navigate:Admin|Assign]"

        status_match = re.search(r"(?:change|update|set|mark)\s+(?:the )?(?:complaint|task)(?: id)?\s*#?(\d+)\s+(?:to|as)\s+([a-zA-Z_ ]+)", normalized)
        if status_match:
            from services.complaint_service import update_status
            complaint_id = int(status_match.group(1))
            status = _status_value(status_match.group(2))
            if not status:
                return "Use a valid status: OPEN, IN_PROGRESS, RESOLVED, or CLOSED."
            complaint = update_status(db, complaint_id, status)
            if not complaint:
                return f"Complaint #{complaint_id} was not found."
            return f"Complaint #{complaint.id} status changed to {complaint.status.value}. [ACTION:navigate:Admin|Assign]"

    if user and user.role == UserRole.EMPLOYEE:
        employee_status_match = re.search(
            r"(?:change|update|set|mark)\s+(?:my\s+)?(?:assigned\s+)?(?:complaint|task)(?: id)?\s*#?(\d+)\s+(?:to|as)\s+([a-zA-Z_ ]+)",
            normalized,
        )
        if employee_status_match:
            from models import Assignation
            from services.complaint_service import update_status
            complaint_id = int(employee_status_match.group(1))
            status = _status_value(employee_status_match.group(2))
            assignment = db.query(Assignation).filter(
                Assignation.complaint_id == complaint_id,
                Assignation.employee_id == user_id,
            ).first()
            if not assignment:
                return f"Complaint #{complaint_id} is not assigned to you, so its status cannot be changed."
            if not status:
                return "Use a valid status: OPEN, IN_PROGRESS, RESOLVED, or CLOSED."
            complaint = update_status(db, complaint_id, status)
            return f"Assigned complaint #{complaint.id} status changed to {complaint.status.value}. [ACTION:navigate:Assigned complaints]"

    if user and user.role == UserRole.ADMIN and any(term in normalized for term in ("users list", "user list", "list users", "show users", "manage users")):
        users = db.query(User).order_by(User.username).all()
        lines = [f"{item.username} | {item.role.value} | {item.email}" for item in users]
        return "Users:\n" + "\n".join(lines) + " [ACTION:navigate:Admin|Users]"

    if any(term in normalized for term in ("show reports", "show me the reports", "show me the reports tab", "open reports", "go to reports", "report page", "reports tab")):
        return "Opening Reports. [ACTION:navigate:Reports]"

    if user and user.role == UserRole.ADMIN and any(term in normalized for term in ("assign complaint", "assign task", "open assign", "go to assign")):
        return "Opening complaint assignment. [ACTION:navigate:Admin|Assign]"

    if user and user.role == UserRole.ADMIN and any(term in normalized for term in ("all complaints", "complaints page", "open complaints")):
        return "Opening the complaints dashboard. [ACTION:navigate:Admin|Complaints]"

    if any(term in normalized for term in ("assigned task", "assigned complaint", "my assignments", "tasks assigned")):
        if not user or user.role != UserRole.EMPLOYEE:
            return "Assigned task lists are available to employee accounts only."
        from models import Assignation
        assignments = db.query(Assignation).filter(Assignation.employee_id == user_id).all()
        if not assignments:
            return "No complaints are assigned to you."
        lines = [f"#{item.complaint.id} {item.complaint.title} | {item.complaint.status.value} | {item.complaint.priority}" for item in assignments]
        return "Your assigned complaints:\n" + "\n".join(lines) + " [ACTION:navigate:Assigned complaints]"

    if any(term in normalized for term in ("create complaint", "create a complaint", "raise complaint", "raise a complaint", "file complaint", "file a complaint", "open complaint", "open a complaint")):
        if not user:
            return "You must be signed in to create a complaint."
        if " about " not in normalized:
            return "Tell me what the complaint is about, for example: create a complaint about a broken streetlight."
        title = normalized.split(" about ", 1)[1].strip().rstrip(".")
        if not title:
            return "Please provide a complaint title and description."
        from services.complaint_service import create_complaint
        complaint = create_complaint(db, title.title(), title, "Medium", user_id)
        destination = "My complaints" if user.role == UserRole.CUSTOMER else "Assigned complaints" if user.role == UserRole.EMPLOYEE else "Admin|Complaints"
        return f"Complaint #{complaint.id} created successfully. [ACTION:navigate:{destination}]"

    if any(term in normalized for term in ("my complaints", "track complaint", "complaint status")):
        from services.complaint_service import list_complaints
        complaints = list_complaints(db, user_id)
        response = "\n".join(f"#{item.id} {item.title}: {item.status.value}" for item in complaints) or "No complaints found."
        return response + " [ACTION:navigate:My complaints]"

    return None


def stream_agent(message, db, user_id):
    local_response = _local_command(message, db, user_id)
    if local_response:
        yield local_response
        return
    if not is_available():
        yield "The AI Assistant is temporarily unavailable. Add OPENAI_API_KEY to enable it."
        return
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_openai import ChatOpenAI
    from ai.agent_tools import make_tools
    prompt = ChatPromptTemplate.from_messages([("system", "You are the CMS agentic assistant. Understand the user's intent from natural language, inspect current-user context when needed, choose the correct tool, execute the action, and report the result. Customers can create complaints and view their complaints. Employees can create complaints, view assigned complaints, and update status only for assigned complaints. Admins can create complaints, list users, assign any complaint to any employee, change any complaint status, and run employee/status reports. Normalize phrases such as employee 3 to employee3 and in progress to IN_PROGRESS. Never claim an action was completed unless a tool confirms it. Use open_page or a returned [ACTION:...] marker whenever the main UI should navigate."), ("human", "{input}"), MessagesPlaceholder("agent_scratchpad")])
    tools = make_tools(db, user_id)
    agent = create_tool_calling_agent(ChatOpenAI(model=CHAT_MODEL, streaming=True), tools, prompt)
    for chunk in AgentExecutor(agent=agent, tools=tools).stream({"input": message}):
        if "output" in chunk:
            yield chunk["output"]
