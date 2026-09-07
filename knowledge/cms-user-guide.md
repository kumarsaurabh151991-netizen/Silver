CMS Application - User Guide
 
The Complaint Management System (CMS) is a role-based application used to raise,
track, assign and resolve complaints.
 
## Roles
 
- CUSTOMER: raises complaints, tracks their own complaints, edits a complaint while it is
  still PENDING, and leaves feedback once it is RESOLVED. A customer can only ever see
  complaints they submitted themselves.
- EMPLOYEE: works on the complaints that an admin has assigned to them. An employee can
  update the status and add remarks on assigned complaints only.
- ADMIN: sees every complaint, creates and deletes complaints, assigns complaints to
  employees, manages users and runs reports.
 
## Complaint lifecycle
 
1. PENDING - the complaint has been submitted but nobody has started work on it.
2. IN_PROGRESS - an employee has started working on the complaint.
3. RESOLVED - the work is finished. The customer can now leave feedback.
 
Only an employee assigned to the complaint, or an admin, may change the status.
Any of PENDING, IN_PROGRESS and RESOLVED can move to any other.
 
## Complaint fields
 
- Title (required, max 200 characters)
- Description (required, max 2000 characters)
- Category (required) - for example Technical, Billing, Service, Product
- Priority - LOW / MEDIUM / HIGH
- Status - PENDING / IN_PROGRESS / RESOLVED
- Remarks - added by the assigned employee or admin
- Feedback - added by the customer after resolution
 
## Pages
 
- /login, /register, /forgot-password - public
- /customer/my-complaints - customer's own complaints
- /employee/my-complaints - complaints assigned to the employee
- /admin/complaints, /admin/users, /admin/assign - admin management
- /reports - Pandas + Plotly analytics