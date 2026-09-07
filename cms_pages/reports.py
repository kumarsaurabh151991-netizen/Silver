import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select

from db import session_scope
from models import Complaint, ComplaintStatus


def load_frame():
    with session_scope() as db:
        rows = [{
            "ID": item.id,
            "Title": item.title,
            "Status": item.status.value,
            "Priority": item.priority,
            "Submitted by": item.creator.username,
            "Assigned to": item.assignments[-1].employee.username if item.assignments else "Unassigned",
            "Created": item.created_at,
            "Updated": item.updated_at,
        } for item in db.scalars(select(Complaint).order_by(Complaint.created_at))]
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["Created"] = pd.to_datetime(frame["Created"])
        frame["Updated"] = pd.to_datetime(frame["Updated"])
    return frame


def render(user):
    st.header("Reports")
    frame = load_frame()
    if frame.empty:
        st.info("No complaints to report yet.")
        return

    report_views = ["Overview", "By user", "Date range", "Raw data"]
    requested_view = st.query_params.get("report_tab", "Overview")
    default_view = requested_view if requested_view in report_views else "Overview"
    report_view = st.radio("Report view", report_views, index=report_views.index(default_view), horizontal=True, label_visibility="collapsed")
    if report_view == "Overview":
        metrics = st.columns(3)
        metrics[0].metric("Total complaints", len(frame))
        metrics[1].metric("Resolved", int(frame["Status"].isin(["RESOLVED", "CLOSED"]).sum()))
        metrics[2].metric("Pending", int(frame["Status"].isin(["OPEN", "IN_PROGRESS"]).sum()))
        left, right = st.columns(2)
        with left:
            st.subheader("Complaints by status")
            counts = frame["Status"].value_counts().rename_axis("Status").reset_index(name="Count")
            st.plotly_chart(px.bar(counts, x="Status", y="Count", color="Status"), use_container_width=True, key="reports_overview_status")
        with right:
            st.subheader("Complaints by priority")
            st.plotly_chart(px.pie(frame, names="Priority"), use_container_width=True, key="reports_overview_priority")
        st.subheader("Complaint trend")
        trend = frame.assign(Date=frame["Created"].dt.date).groupby(["Date", "Status"], as_index=False).size()
        st.plotly_chart(px.line(trend, x="Date", y="size", color="Status", markers=True), use_container_width=True, key="reports_overview_trend")

    elif report_view == "By user":
        customer_col, employee_col = st.columns(2)
        with customer_col:
            selected_customer = st.selectbox("Customer", ["ALL"] + sorted(frame["Submitted by"].unique().tolist()))
        with employee_col:
            employee_options = ["ALL"] + sorted(frame["Assigned to"].unique().tolist())
            requested_employee = st.query_params.get("report_employee", "ALL")
            employee_index = employee_options.index(requested_employee) if requested_employee in employee_options else 0
            selected_employee = st.selectbox("Employee", employee_options, index=employee_index)
        filtered = frame
        if selected_customer != "ALL":
            filtered = filtered[filtered["Submitted by"] == selected_customer]
        if selected_employee != "ALL":
            filtered = filtered[filtered["Assigned to"] == selected_employee]
        requested_status = st.query_params.get("report_status")
        if requested_status and requested_status != "ALL":
            filtered = filtered[filtered["Status"] == requested_status]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        if not filtered.empty:
            counts = filtered["Status"].value_counts().rename_axis("Status").reset_index(name="Count")
            st.plotly_chart(px.bar(counts, x="Status", y="Count", color="Status"), use_container_width=True, key="reports_by_user_status")

    elif report_view == "Date range":
        minimum = frame["Created"].min().date()
        maximum = frame["Created"].max().date()
        selected_dates = st.date_input("Created between", value=(minimum, maximum), min_value=minimum, max_value=maximum)
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            filtered = frame[(frame["Created"].dt.date >= start_date) & (frame["Created"].dt.date <= end_date)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)

    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", frame.to_csv(index=False), "cms-complaints.csv", "text/csv")
