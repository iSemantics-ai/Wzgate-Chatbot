import streamlit as st
import asyncio
import ast
from pathlib import Path
import uuid
import json

from routers import chatbot_interface, initialize_rag  # Your chatbot logic
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------------------
# Page Config (Set before anything else)
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Real Estate Chatbot",
    page_icon="🏠",
    layout="wide",
)

# -------------------------------------------------------------------
# Custom CSS for Styling
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Overall login container */
    .login-container {
        background-color: #f0f0f0;
        padding: 2em;
        border-radius: 8px;
        margin: 2em auto;
        max-width: 500px;
    }
    /* Title text */
    .login-title {
        font-family: "Helvetica Neue", sans-serif;
        color: #2c3e50;
        text-align: center;
        font-size: 1.8rem;
        margin-bottom: 0.5em;
    }
    /* Subtitle text */
    .login-subtitle {
        font-family: "Arial", sans-serif;
        color: #7f8c8d;
        text-align: center;
        font-size: 1rem;
        margin-bottom: 1.5em;
    }
    /* Icon column styling */
    .icon-column {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .icon-column img {
        max-width: 24px;
    }
    /* Make text inputs more spaced out */
    .stTextInput {
        margin-bottom: 1rem;
    }
    /* Style the radio buttons */
    .stRadio {
        margin-bottom: 1rem;
    }
    /* A custom style for the button (Streamlit's default button is limited) */
    .stButton>button {
        background-color: #2980b9 !important;
        color: #fff !important;
        border: none;
        padding: 0.6em 1.2em;
        border-radius: 4px;
        font-size: 1rem;
        cursor: pointer;
        margin-top: 1em;
    }
    .stButton>button:hover {
        background-color: #3498db !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------------------
# Google Sheets Setup
# -------------------------------------------------------------------
def init_google_sheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(credentials)
    return client.open("users_db").sheet1  # Adjust the name if different

sheet = init_google_sheets()

# -------------------------------------------------------------------
# Authentication State
# -------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
def check_user_credentials(username: str, password: str) -> bool:
    ws = init_google_sheets()
    records = ws.get_all_records()
    for row in records:
        if row.get("username") == username and row.get("password") == password:
            return True
    return False

def register_new_user(username: str, password: str) -> bool:
    ws = init_google_sheets()
    records = ws.get_all_records()
    for row in records:
        if row.get("username") == username:
            return False  # user already exists
    ws.append_row([username, password])
    return True

# -------------------------------------------------------------------
# Icons
# -------------------------------------------------------------------
user_icon_path = Path("images/user_name.png")
pass_icon_path = Path("images/password.png")
reg_icon_path  = Path("images/register.png")

# -------------------------------------------------------------------
# Login / Registration UI
# -------------------------------------------------------------------
def show_auth_ui():
    # Inline CSS to make icons smaller and center/enlarge the buttons
    st.markdown(
        """
        <style>
        .icon-column img {
            width: 20px !important;  /* smaller icon width */
            height: auto !important;
        }
        /* Center the buttons and make them bigger */
        .center-button .stButton button {
            margin: 0 auto;
            display: block;
            width: 60%;           /* adjust width as desired */
            padding: 0.8em 1.2em;
            font-size: 1.05rem;   /* slightly larger text */
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("<h1 class='title-text'>Authentication</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle-text'>Access the Real Estate Chatbot</p>", unsafe_allow_html=True)

    tabs = st.tabs(["Create new account", "Login to existing account"])

    # --- Create new account ---
    with tabs[0]:
        st.write("Create a unique username and password:")
        col_icon_u, col_input_u = st.columns([1, 20])
        with col_icon_u:
            st.markdown("<div class='icon-column'>", unsafe_allow_html=True)
            if user_icon_path.exists():
                # smaller size for image as icon
                st.image(str(user_icon_path), width=10, use_container_width =True)
            else:
                st.write("👤")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_input_u:
            new_username = st.text_input("Create a unique username", key="new_username")

        col_icon_p, col_input_p = st.columns([1, 20])
        with col_icon_p:
            st.markdown("<div class='icon-column'>", unsafe_allow_html=True)
            if pass_icon_path.exists():
                st.image(image=str(pass_icon_path), width=10, use_container_width =True)
            else:
                st.write("🔒")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_input_p:
            new_password = st.text_input("Create a password", type="password", key="new_password")

        # Center & enlarge the "Create account" button
        with st.container():
            st.markdown("<div class='center-button'>", unsafe_allow_html=True)
            if st.button("Create account"):
                if new_username and new_password:
                    success = register_new_user(new_username, new_password)
                    if success:
                        st.success("Account created successfully! Please log in.")
                    else:
                        st.error("Username already exists. Please choose a different one.")
                else:
                    st.warning("Please enter a username and password.")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- Login to existing account ---
    with tabs[1]:
        st.write("Enter your unique username and password:")
        col_icon_u, col_input_u = st.columns([1, 20])
        with col_icon_u:
            st.markdown("<div class='icon-column'>", unsafe_allow_html=True)
            if user_icon_path.exists():
                st.image(image=str(user_icon_path), width=10, use_container_width =True)
            else:
                st.write("👤")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_input_u:
            login_username = st.text_input("Enter your username", key="login_username")

        col_icon_p, col_input_p = st.columns([1, 20])
        with col_icon_p:
            st.markdown("<div class='icon-column'>", unsafe_allow_html=True)
            if pass_icon_path.exists():
                st.image(image=str(pass_icon_path),width=10, use_container_width =True)
            else:
                st.write("🔒")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_input_p:
            login_password = st.text_input("Enter your password", type="password", key="login_password")

        # Center & enlarge the "Login" button
        with st.container():
            st.markdown("<div class='center-button'>", unsafe_allow_html=True)
            if st.button("Login"):
                if check_user_credentials(login_username, login_password):
                    st.session_state.authenticated = True
                    st.session_state.username = login_username
                    st.success("Logged in successfully!")
                else:
                    st.error("Invalid username or password.")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # close auth-container


# Example usage:
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    show_auth_ui()
    st.stop()


# -------------------------------------------------------------------
# Main Chat Code (Runs if Authenticated)
# -------------------------------------------------------------------
# Prepare your chat keys in session_state
session_key = f"messages_{st.session_state.session_id}"
fixed_clicked_key = f"fixed_clicked_{st.session_state.session_id}"
fixed_button_processed_key = f"fixed_button_processed_{st.session_state.session_id}"
last_assistant_response_key = f"last_assistant_response_{st.session_state.session_id}"

if session_key not in st.session_state:
    st.session_state[session_key] = []
if fixed_clicked_key not in st.session_state:
    st.session_state[fixed_clicked_key] = False
if fixed_button_processed_key not in st.session_state:
    st.session_state[fixed_button_processed_key] = False
if last_assistant_response_key not in st.session_state:
    st.session_state[last_assistant_response_key] = ""


# -----------------------------------------------------------------------------
# Load Logos
# -----------------------------------------------------------------------------
isemantics_logo_path = Path("images/isemantics_logo.png")


# -----------------------------------------------------------------------------
# Top Header with Title + Logos
# -----------------------------------------------------------------------------
header_col1, header_col2, header_col3 = st.columns([1, 3, 1])
with header_col1:
    if isemantics_logo_path.exists():
        st.image(str(isemantics_logo_path), use_container_width=True)
    else:
        st.write("**isemantics logo**")
with header_col2:
    st.markdown(
        """
        <h1 style="text-align:center; margin-top:-20px;">
             Real Estate Chatbot
        </h1>
        <h5 style="text-align:center; margin-top:-20px;">
            Demo
        </h5>
        """,
        unsafe_allow_html=True
    )



# -----------------------------------------------------------------------------
# Sidebar with Descriptive Text
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <h3>About This Chatbot</h3>
        <p>
        <strong> Real Estate Chatbot</strong> is an advanced conversational assistant 
        developed by <strong>isemantics company</strong>. This intelligent chatbot leverages 
        both <em>Retrieval-Augmented Generation (RAG)</em> and a specialized <em>Units chatbot</em> 
        to help you find the perfect property.
        </p>
        <ul>
          <li><strong>RAG Chatbot:</strong> Retrieves relevant real estate data from our extensive 
          knowledge base to answer general inquiries and provide market insights.</li>
          <li><strong>Units Chatbot:</strong> Engages in detailed conversations to capture your 
          specific property requirements, ensuring personalized recommendations.</li>
        </ul>
        <p>
        Whether you’re looking for a new apartment, villa, or any type of property, 
        our system guides you through a dynamic conversation—analyzing your needs and 
        prompting follow-up questions to help you discover your ideal place.
        </p>
        """,
        unsafe_allow_html=True
    )

# -----------------------------------------------------------------------------
# Main Chat Section
# -----------------------------------------------------------------------------

def is_arabic(text: str) -> bool:
    return any('\u0600' <= c <= '\u06FF' for c in text)

if st.button("Clear History"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state[session_key] = []
    st.session_state[fixed_clicked_key] = False
    st.session_state[fixed_button_processed_key] = False
    st.session_state[last_assistant_response_key] = ""
    


st.write("Ask any questions about real estate, and I'll assist you with finding the perfect place!")

for message in st.session_state[session_key]:
    if message["role"] == "user":
        with st.chat_message("user", avatar="images/man.png"):
            st.write(message["content"])
    elif message["role"] == "assistant":
        with st.chat_message("assistant", avatar="images/estate-agent.png"):
            st.write(message["content"])
# -----------------------------------------------------------------------------
# Capture New User Input
# -----------------------------------------------------------------------------
prompt = st.chat_input("Type your question here...", key="chat_input")
if prompt:
    # Append and display the user input.
    st.session_state[session_key].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="images/man.png"):
        st.write(prompt)

    # Get the assistant's response.
    with st.chat_message("assistant", avatar="images/estate-agent.png"):
        with st.spinner("Thinking..."):
            response = asyncio.run(chatbot_interface(prompt, st.session_state.session_id))
            assistant_response = response.get("text", "Sorry, I couldn't process your request.")
            st.write(assistant_response)

        st.session_state[session_key].append({"role": "assistant", "content": assistant_response})
            # Update the assistant's response in session state.
        st.session_state[last_assistant_response_key] = assistant_response

        lang = "ar" if is_arabic(assistant_response) else "en"
        fixed_message = (
            "هل تريد متابعة البحث، هل المعلومات المقدمة كافية؟"
            if lang == "ar"
            else "Would you like to proceed with the search, is the provided information sufficient?"
        )
        # If this new assistant response contains the fixed text,
        # reset the fixed-button flags so the button can appear.
        if fixed_message in assistant_response:
            st.session_state[fixed_button_processed_key] = False
            st.session_state[fixed_clicked_key] = False

if st.session_state[last_assistant_response_key]:
    lang = "ar" if is_arabic(st.session_state[last_assistant_response_key]) else "en"
    fixed_message = (
        "هل تريد متابعة البحث، هل المعلومات المقدمة كافية؟"
        if lang == "ar"
        else "Would you like to proceed with the search, is the provided information sufficient?"
    )
    button_label = "نعم ابحث" if lang == "ar" else "Yes search"# -----------------------------------------------------------------------------
# Debug Output (should now show updated values)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Fixed-Message Button: Display Only if the Assistant's Response Contains the Fixed Text
# -----------------------------------------------------------------------------
    if (fixed_message in st.session_state[last_assistant_response_key]) and not st.session_state[fixed_button_processed_key]:
        if st.button(button_label):
            st.session_state[fixed_clicked_key] = True

if st.session_state[fixed_clicked_key] and not st.session_state[fixed_button_processed_key]:
    # Simulate the user input for the fixed message button.
    if not any(msg["role"] == "user" and msg["content"] == button_label for msg in st.session_state[session_key]):
        st.session_state[session_key].append({"role": "user", "content": button_label})
        with st.chat_message("user", avatar="images/man.png"):
            st.write(button_label)
    # Process this simulated input.
    response_fixed = asyncio.run(chatbot_interface(button_label, st.session_state.session_id))
    fixed_response = response_fixed.get("text", "Sorry, I couldn't process your request.")
    st.session_state[session_key].append({"role": "assistant", "content": fixed_response})
    with st.chat_message("assistant", avatar="images/estate-agent.png"):
        st.write(fixed_response)
    st.session_state[fixed_button_processed_key] = True

# -----------------------------------------------------------------------------
# RAG Initialization (once)
# # -----------------------------------------------------------------------------
if "rag_initialized" not in st.session_state:
    with st.spinner("Initializing RAG components..."):
        asyncio.run(initialize_rag())
    st.session_state.rag_initialized = True
