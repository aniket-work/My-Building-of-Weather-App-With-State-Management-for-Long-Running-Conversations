"""
Main Streamlit application for the Weather Assistant.
"""

import os
import time
import uuid
import asyncio
import streamlit as st
from pathlib import Path

# Import application modules
from src.utils import (
    load_environment_variables,
    load_yaml_config,
    get_example_questions,
    initialize_database,
    format_message_for_display
)
from src.tools import load_search_tool
from src.agent import create_agent
from src.constants import PAGE_TITLE, PAGE_ICON, LAYOUT, CSS, DEFAULT_DB_PATH

# Load environment variables
load_environment_variables()

# Load configurations
config = load_yaml_config()
example_questions = get_example_questions()

# Page configuration
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT
)

# Display CSS
st.markdown(CSS, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize the session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = str(uuid.uuid4())

    if "question_submitted" not in st.session_state:
        st.session_state.question_submitted = False

    if "current_question" not in st.session_state:
        st.session_state.current_question = ""

    if "agent" not in st.session_state:
        # Create database directory if it doesn't exist
        db_path = config.get("database", {}).get("path", DEFAULT_DB_PATH)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database connection
        initialize_database(db_path)

        # Load search tool
        search_tool = load_search_tool()

        # Get model configuration
        model_name = config.get("model", {}).get("name", "Llama-3.3-70b-Specdec")
        system_prompt = config.get("model", {}).get("system_prompt", "")

        # Create the agent
        st.session_state.agent = create_agent(
            model_name=model_name,
            tools=[search_tool],
            system_prompt=system_prompt,
            db_path=db_path,
            verbose=False
        )


def handle_user_input():
    """Handle user input from the chat interface."""
    # Get the user input either from the chat input or from the example question
    if st.session_state.question_submitted:
        user_input = st.session_state.current_question
        st.session_state.question_submitted = False
        st.session_state.current_question = ""
    else:
        user_input = st.session_state.user_input

    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Get agent response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")

            # Get response from agent
            responses = st.session_state.agent.chat(
                message=user_input,
                thread_id=st.session_state.conversation_id
            )

            # Process all responses
            all_messages = []
            for response in responses:
                messages = response.get("messages", [])
                for message in messages:
                    formatted_message = format_message_for_display(message)
                    if formatted_message and formatted_message != "🔍 Searching for information...":
                        all_messages.append(formatted_message)

            # Combine and deduplicate messages
            if all_messages:
                # Use the last non-search message as the final response
                final_response = all_messages[-1]
                message_placeholder.markdown(final_response)

                # Add assistant message to chat history
                st.session_state.messages.append({"role": "assistant", "content": final_response})
            else:
                fallback_response = "I couldn't retrieve the weather information at this time."
                message_placeholder.markdown(fallback_response)
                st.session_state.messages.append({"role": "assistant", "content": fallback_response})


def set_example_question(question):
    """Set an example question and mark it for submission."""
    st.session_state.current_question = question
    st.session_state.question_submitted = True
    st.rerun()


def display_chat_history():
    """Display the chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def create_new_conversation():
    """Create a new conversation."""
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()


def main():
    """Main application function."""
    # Initialize session state
    initialize_session_state()

    # App header
    st.title(f"{PAGE_ICON} {config.get('app', {}).get('title', PAGE_TITLE)}")
    st.markdown(config.get('app', {}).get('description', ""))

    # Process any pending example question
    if st.session_state.question_submitted:
        handle_user_input()

    # Sidebar with controls
    with st.sidebar:
        st.title("⚙️ Settings")

        # Create new conversation button
        if st.button("New Conversation", key="new_conv"):
            create_new_conversation()

        # Display conversation ID
        st.divider()
        st.subheader("Conversation Info")
        st.text(f"ID: {st.session_state.conversation_id}")

        # Example questions
        st.divider()
        st.subheader("Example Questions")
        for question in example_questions:
            if st.button(question, key=f"q_{hash(question)}"):
                set_example_question(question)

    # Main chat interface
    display_chat_history()

    # Chat input
    st.chat_input("Ask me about the weather anywhere...", key="user_input", on_submit=handle_user_input)


if __name__ == "__main__":
    main()