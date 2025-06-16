import streamlit as st
from datetime import datetime, timedelta
from fpdf import FPDF
import os
import base64
from supabase import create_client, Client

# ---------- Supabase Config ----------
url = "https://msxunskycuubjzjvdbii.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1zeHVuc2t5Y3V1Ymp6anZkYmlpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAwNDc5OTgsImV4cCI6MjA2NTYyMzk5OH0.LamB96kHADB0Va0ZGj8K-uBcgDRFmiVpcvKveOgJtVQ"
supabase: Client = create_client(url, key)

# ---------- Helper Functions ----------
def authenticate_user(email, password):
    result = supabase.table("users").select("*").eq("email", email).eq("password", password).single().execute()
    return result.data

def get_sub_users(created_by):
    result = supabase.table("users").select("id, name, email").eq("created_by", created_by).execute()
    return result.data or []

def get_all_users():
    result = supabase.table("users").select("id, name, email, password").execute()
    return result.data or []

def add_user(name, email, password, created_by):
    supabase.table("users").insert({
        "name": name,
        "email": email,
        "password": password,
        "role": "user",
        "created_by": created_by
    }).execute()
    st.success("User added successfully.")

def delete_user(user_id):
    supabase.table("transactions").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("id", user_id).execute()
    st.success("User and their transactions deleted successfully.")

def add_transaction(user_id, amount, type_, description):
    timestamp = datetime.now().isoformat()
    supabase.table("transactions").insert({
        "user_id": user_id,
        "amount": amount,
        "type": type_,
        "description": description,
        "timestamp": timestamp
    }).execute()
    st.success("Transaction added successfully.")

def get_transactions(user_id):
    result = supabase.table("transactions").select("*").eq("user_id", user_id).execute()
    return result.data or []

def get_all_transactions():
    result = supabase.table("transactions").select("*").execute()
    return result.data or []

def delete_transaction(transaction_id):
    supabase.table("transactions").delete().eq("id", transaction_id).execute()
    st.success("Transaction deleted successfully.")

def delete_transactions_by_date(start_date, end_date):
    supabase.table("transactions").delete().gte("timestamp", start_date).lte("timestamp", end_date).execute()
    st.success("Transactions between dates deleted successfully.")

def update_password(user_id, new_password):
    supabase.table("users").update({"password": new_password}).eq("id", user_id).execute()
    st.success("Password updated successfully.")

def export_pdf(user, transactions):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    today = datetime.today()
    bill_start = today.replace(day=13) if today.day >= 13 else today.replace(month=today.month-1 if today.month > 1 else 12, day=13)
    next_month = bill_start.month % 12 + 1
    year = bill_start.year + (1 if next_month == 1 else 0)
    bill_end = datetime(year=year, month=next_month, day=12)
    due_date = bill_start + timedelta(days=50)

    pdf.cell(200, 10, txt=f"Statement for {user['name']} ({user['email']})", ln=True)
    pdf.cell(200, 10, txt=f"Billing Period: {bill_start.date()} to {bill_end.date()}", ln=True)
    pdf.cell(200, 10, txt=f"Due Date: {due_date.date()}", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(50, 10, "Date", 1)
    pdf.cell(30, 10, "Type", 1)
    pdf.cell(40, 10, "Amount", 1)
    pdf.cell(70, 10, "Description", 1)
    pdf.ln()

    pdf.set_font("Arial", size=12)
    total_due = 0
    for t in transactions:
        if t['type'] == 'debit':
            total_due += t['amount']
        description = (t['description'][:30] + '...') if len(t['description']) > 33 else t['description']
        pdf.cell(50, 10, t['timestamp'][:19], 1)
        pdf.cell(30, 10, t['type'].upper(), 1)
        pdf.cell(40, 10, f"Rs.{t['amount']:.2f}", 1)
        pdf.cell(70, 10, description, 1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"TOTAL DUE (to be paid by {due_date.date()}): Rs.{total_due:.2f}", ln=True)

    filename = f"{user['name'].replace(' ', '_')}_due_{due_date.date()}.pdf"
    pdf.output(filename)

    with open(filename, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<a href="data:application/octet-stream;base64,{base64_pdf}" download="{filename}">Download PDF Statement</a>'
        st.markdown(pdf_display, unsafe_allow_html=True)

    os.remove(filename)

# ---------- UI ----------
st.set_page_config(page_title="Transaction Manager", layout="centered")
st.title("📑 Supabase Transaction Manager")

email = st.text_input("Enter your email")
password = st.text_input("Enter your password", type="password")

if email and password:
    user = authenticate_user(email, password)
    if not user:
        st.warning("Invalid email or password.")
    else:
        is_admin = user['role'] == 'admin'
        st.success(f"Welcome, {user['name']}")

        if is_admin:
            tabs = st.tabs(["➕ Add User", "💰 Add Transaction", "📄 View Statement", "📤 Export as PDF", "🔐 Passwords", "👥 View All Users", "🗑️ Delete Transactions", "🔁 Change Password"])

            with tabs[0]:
                name = st.text_input("Name")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password", type="password")
                if st.button("Add User"):
                    add_user(name, new_email, new_password, created_by=user['id'])

            with tabs[1]:
                sub_users = get_sub_users(user['id'])
                selected = st.selectbox("Select Sub-User", sub_users, format_func=lambda x: x['name'])
                amount = st.number_input("Amount", format="%.2f")
                type_ = st.radio("Type", ["credit", "debit"])
                description = st.text_input("Description")
                if st.button("Submit Transaction"):
                    add_transaction(selected['id'], amount, type_, description)

            with tabs[2]:
                sub_users = get_sub_users(user['id'])
                selected = st.selectbox("Select Sub-User to View", sub_users, format_func=lambda x: x['name'])
                transactions = get_transactions(selected['id'])
                st.dataframe(transactions, use_container_width=True)

            with tabs[3]:
                sub_users = get_sub_users(user['id'])
                selected = st.selectbox("Select Sub-User for PDF", sub_users, format_func=lambda x: x['name'])
                transactions = get_transactions(selected['id'])
                export_pdf(selected, transactions)

            with tabs[4]:
                users = get_all_users()
                st.dataframe([{"Name": u['name'], "Email": u['email'], "Password": u['password']} for u in users], use_container_width=True)

            with tabs[5]:
                all_users = get_all_users()
                all_transactions = get_all_transactions()
                user_due_map = {}
                for user_data in all_users:
                    uid = user_data['id']
                    user_name = user_data['name']
                    due = sum(t['amount'] for t in all_transactions if t['user_id'] == uid and t['type'] == 'debit')
                    user_due_map[user_name] = due

                st.dataframe([{"Name": name, "Total Due": due} for name, due in user_due_map.items()], use_container_width=True)
                grand_total = sum(user_due_map.values())
                st.info(f"Grand Total Due from All Users: Rs.{grand_total:.2f}")

            with tabs[6]:
                start_date = st.date_input("Start Date")
                end_date = st.date_input("End Date")
                if st.button("Delete Transactions Between Dates"):
                    delete_transactions_by_date(start_date.isoformat(), end_date.isoformat())

            with tabs[7]:
                new_pass = st.text_input("Enter New Password", type="password")
                if st.button("Change Password"):
                    update_password(user['id'], new_pass)

        else:
            st.header("📄 Your Transactions")
            transactions = get_transactions(user['id'])
            st.dataframe(transactions, use_container_width=True)

            st.header("📤 Export as PDF")
            export_pdf(user, transactions)

            st.header("🔁 Change Password")
            new_pass = st.text_input("Enter New Password", type="password")
            if st.button("Change Password"):
                update_password(user['id'], new_pass)
