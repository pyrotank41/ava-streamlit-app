from dotenv import load_dotenv
# from auth_utils import get_auth_data
from loguru import logger
import pandas as pd
import streamlit as st

from config import ENV_FILE_PATH

def chat_page():
    st.write("### AVA quote generator")

    load_dotenv(ENV_FILE_PATH)


    with st.sidebar:
        # st.button("Clear Chat", on_click=clear_chat_history)
        st.write("**Tip**: *To clear chat history, refresh the page!*")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        logger.debug("Chat history initialized")

    # Initialize OrderProcessor
    if "ava" not in st.session_state and "base_audit" in st.session_state:
        # st.write(st.session_state.get("auth_data"))
        # audit_metadata = {"_user": "}
        base_audit = st.session_state.get("base_audit")
        # st.session_state.ava = AVA(base_audit=base_audit)
        logger.debug("AVA initialized")

    # Custom CSS to set the width of the dataframe
    st.markdown(
        """
    <style>
        .stDataFrame {
            width: 100%;
        }
        .dataframe {
            font-size: 14px;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    def display_quote_df(df):
        container = st.container()

        container.dataframe(
            df,
            use_container_width=True,
            column_config={
                "description": st.column_config.TextColumn(
                    "Description",
                    width=350,
                    help="Product description",
                ),
            },
            hide_index=True,
        )

    # Display chat messages from history on app rerun
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.chat_message("user"):
                container = st.container()
                user_message_content = str(message["content"])
                container.write(
                    f"{user_message_content}",
                    unsafe_allow_html=True,
                )
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])

                attachments = message.get("attachments", [])

                if attachments:
                    st.write("*Attachments*:")
                    for attachment in attachments:
                        if isinstance(attachment, pd.DataFrame):
                            display_quote_df(attachment)
                        else:
                            logger.warning(
                                "Attachment of type {} not supported", type(attachment)
                            )
                            st.write(attachment)

                # # Create a container for the buttons
                # button_container = st.empty()

                # # Use markdown to create a div that will contain both buttons
                # button_container.markdown(
                #     f"""
                #     <div>
                #         <div class="feedback-button">
                #             {st.button("👍", key=f"thumbs_up_{i}", on_click=handle_feedback, args=(i, "positive"))}
                #         </div>
                #         <div class="feedback-button">
                #             {st.button("👎", key=f"thumbs_down_{i}", on_click=handle_feedback, args=(i, "negative"))}
                #         </div>
                #     </div>
                #     """,
                #     unsafe_allow_html=True
                # )

                # st.button("👍", key=f"thumbs_up_{i}", on_click=handle_feedback, args=(i, "positive"))
                # st.button("👎", key=f"thumbs_down_{i}", on_click=handle_feedback, args=(i, "negative"))

                # # Display feedback if it exists
                # if "feedback" in message:
                #     with st.expander("Feedback Given"):
                #         st.write(f"*Feedback: {message['feedback']}*")
                #         if "feedback_reason" in message:
                #             st.write(f"*Reason: {message['feedback_reason']}*")

    def append_user_message(user_message):
        """Append user message to chat history"""
        st.session_state.messages.append({"role": "user", "content": user_message})

    def append_assistant_message(assistant_message):
        """Append assistant message to chat history"""

        if isinstance(assistant_message, str):
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_message}
            )

        else:
            message = assistant_message.message
            attachments = assistant_message.attachments

            st.session_state.messages.append(
                {"role": "assistant", "content": message, "attachments": attachments}
            )

    def respond_to_user_input():
        """Callback function to respond to user input"""
        logger.debug("Responding to chat")

        # Get user input
        user_message = st.session_state.get("chat_input")
        # ava: AVA = st.session_state.ava

        # response = ava.process_user_message(user_message)

        append_user_message(user_message)
        # append_assistant_message(response)

    st.chat_input(
        placeholder="Type a message...",
        key="chat_input",
        on_submit=respond_to_user_input,
        args=None,
        kwargs=None,
    )
