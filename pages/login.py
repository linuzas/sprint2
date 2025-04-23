import streamlit as st
from database.supabase_helpers import create_client
import os

# --- Hide Streamlit sidebar ---
st.set_page_config(page_title="Login | Crypto Advisor")
st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- Initialize Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Redirect if already logged in ---
if all(k in st.session_state for k in ["user", "access_token", "refresh_token"]):
    st.success("✅ You are already logged in!")
    st.switch_page("app.py")

# --- UI ---
st.title("🔐 Login to Crypto Advisor")

mode = st.radio("Choose Action", ["Login", "Sign Up"], horizontal=True)

if mode == "Login":
    st.subheader("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            try:
                res = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                session = supabase.auth.get_session()
                user = supabase.auth.get_user(session.access_token)
                st.session_state["user"] = user.user
                st.session_state["access_token"] = session.access_token
                st.session_state["refresh_token"] = session.refresh_token
                st.success("🎉 Logged in successfully!")
                st.switch_page("app.py")
            except Exception:
                st.error("❌ Login failed. Please check your email and password.")

else:
    st.subheader("Sign Up")
    with st.form("signup_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        username = st.text_input("Preferred Username")
        submitted = st.form_submit_button("Sign Up")

        if submitted:
            if not username.strip():
                st.warning("⚠️ Username is required.")
            else:
                try:
                    # Ensure username is unique
                    existing = supabase.table("users").select("id").eq("username", username).execute()
                    if existing.data:
                        st.warning("⚠️ Username already taken.")
                    else:
                        res = supabase.auth.sign_up({
                            "email": email,
                            "password": password
                        })
                        session = supabase.auth.get_session()

                        if session:
                            user = supabase.auth.get_user(session.access_token)
                            auth_user_id = user.user.id

                            # Add user to custom users table
                            supabase.table("users").insert({
                                "auth_user_id": auth_user_id,
                                "username": username
                            }).execute()

                            # Store session
                            st.session_state["user"] = user.user
                            st.session_state["access_token"] = session.access_token
                            st.session_state["refresh_token"] = session.refresh_token
                            st.success("🎉 Registered and logged in!")
                            st.switch_page("app.py")
                        else:
                            st.success("🎉 Registered! Please confirm your email before logging in.")
                except Exception as e:
                    st.error("❌ Sign up failed. Try again or use a different email.")
