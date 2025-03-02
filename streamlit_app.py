import streamlit as st
import asyncio
import ast
from pathlib import Path

# Import your existing async chatbot interface and RAG initialization.
from routers import chatbot_interface  # your async function that processes chat input
from routers import initialize_rag
import uuid
import json  # Import the json module as an alternative parser


# -----------------------------------------------------------------------------
# Page Config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Wzgate Real Estate Chatbot",
    page_icon="🏠",
    layout="wide",
)

# -----------------------------------------------------------------------------
# Generate a Unique Session ID
# -----------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Use a key that incorporates the unique session ID for storing messages.
session_key = f"messages_{st.session_state.session_id}"
if session_key not in st.session_state:
    st.session_state[session_key] = []

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
wzgate_logo_path = Path("images/wzgate_logo_s.jpg")

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
            Wzgate Real Estate Chatbot
        </h1>
        <h5 style="text-align:center; margin-top:-20px;">
            Demo
        </h5>
        """,
        unsafe_allow_html=True
    )
with header_col3:
    if wzgate_logo_path.exists():
        st.image(str(wzgate_logo_path), use_container_width=True)
    else:
        st.write("**Wzgate logo**")

# -----------------------------------------------------------------------------
# Sidebar with Descriptive Text
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <h3>About This Chatbot</h3>
        <p>
        <strong>Wzgate Real Estate Chatbot</strong> is an advanced conversational assistant 
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
    
st.write("Ask any questions about real estate, and I'll assist you with finding the perfect place!")
for message in st.session_state[session_key]:
    if message["role"] == "user":
        with st.chat_message("user", avatar="images/man.png"):
            st.write(message["content"])
    elif message["role"] == "assistant":
        with st.chat_message("assistant", avatar="images/estate-agent.png"):
            st.write(message["content"])

print("🔑 session_key",session_key)
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
            # st.write(assistant_response)  
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
    button_label = "نعم ابحث" if lang == "ar" else "Yes search"
# -----------------------------------------------------------------------------
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

    # Append and store the assistant’s reply.
  
# -----------------------------------------------------------------------------
# RAG Initialization (runs once)
# -----------------------------------------------------------------------------
if "rag_initialized" not in st.session_state:
    with st.spinner("Initializing RAG components..."):
        asyncio.run(initialize_rag())
    st.session_state.rag_initialized = True