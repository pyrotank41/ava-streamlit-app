import os
import requests
import streamlit as st
from azure.storage.blob import BlobServiceClient, BlobClient
from dotenv import load_dotenv

from config import ENV_FILE_PATH, BACKEND_URL
# from insert_vectors import update_vector_store_with_new_documents

load_dotenv(ENV_FILE_PATH)
# Azure Blob Storage configuration
connection_string = os.getenv("AZURE_AVA_POC_APPS_CONNECTION_STRING")
if connection_string is None:
    st.error("Azure Blob Storage connection string is not set. Please set the AZURE_AVA_POC_APPS_CONNECTION_STRING environment variable.")
    st.stop()
container_name = "product-knowledge"
# azure_folder = os.getenv("TENANT_NAME", "dhupar")

# st.logo("streamlit_app/images/pragmaticai_logo.png")

def update_vector_store_with_new_documents():
    url = f"{BACKEND_URL}/api/ava/re-embed-tenant-documents"
    headers = {"Authorization": f"Bearer {st.session_state.get('access_token')}"}
    response = requests.post(url, data={"tenant_id": st.session_state.get("selected_tenant_id")}, headers=headers)
    if response.status_code == 200:
        st.success("Documents re-embedded successfully")
    else:
        st.error("Failed to re-embed documents")


def product_knowledge_page():
    
    # # Configure storage backend
    use_azure = (
        os.getenv("USE_AZURE_STORAGE_FOR_PRODUCT_KNOWLEDGE", "true").lower() == "true"
    )
    azure_folder = st.session_state.get("selected_tenant_id")
    # azure_folder = "dhupar"
    # Function to get all .txt files
    def get_txt_files():
        if use_azure:
            blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
            
            container_client = blob_service_client.get_container_client(container_name)
            prefix = f"{azure_folder}/" if azure_folder else ""
            return [
                blob.name[len(prefix) :]
                for blob in container_client.list_blobs(name_starts_with=prefix)
                if blob.name.endswith(".txt") and "/" not in blob.name[len(prefix) :]
            ]
        else:
            folder_path = "knowledgebase"
            return [f for f in os.listdir(folder_path) if f.endswith(".txt")]

    # Function to read file content
    def read_file(file_name):
        if use_azure:
            full_path = f"{azure_folder}/{file_name}" if azure_folder else file_name
            blob_client = BlobClient.from_connection_string(
                connection_string, container_name, full_path
            )
            return blob_client.download_blob().content_as_text()
        else:
            folder_path = "knowledgebase"
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, "r") as file:
                return file.read()

    # Function to write file content
    def write_file(file_name, content):
        if use_azure:
            full_path = f"{azure_folder}/{file_name}" if azure_folder else file_name
            blob_client = BlobClient.from_connection_string(
                connection_string, container_name, full_path
            )
            blob_client.upload_blob(content, overwrite=True)
            update_vector_store_with_new_documents()
        else:
            folder_path = "knowledgebase"
            file_path = os.path.join(folder_path, file_name)
            with open(file_path, "w") as file:
                file.write(content)

    # Function to delete file
    def delete_file(file_name):
        if use_azure:
            full_path = f"{azure_folder}/{file_name}" if azure_folder else file_name
            blob_client = BlobClient.from_connection_string(
                connection_string, container_name, full_path
            )
            blob_client.delete_blob()
            setattr(st.session_state, "delete_file_button_clicked", False)
            update_vector_store_with_new_documents()
        else:
            folder_path = "knowledgebase"
            file_path = os.path.join(folder_path, file_name)
            os.remove(file_path)

        st.success(f"Deleted {st.session_state.selected_file}")
        st.session_state.selected_file = None

    def new_file_button_clicked():
        st.session_state["new_file"] = True
        st.session_state["edit_mode"] = False

    def enter_edit_mode():
        st.session_state["edit_mode"] = True

    def is_edit_mode():
        return st.session_state.get("edit_mode", False)

    with st.sidebar:
        st.button(
            "Add New File", key="new_file_button", on_click=new_file_button_clicked
        )

        files = get_txt_files()
        selected_file = st.radio("Select a file", files, key="file_selector")
        if not st.session_state.get("new_file", False):
            st.session_state.selected_file = selected_file

    # Main content area
    if st.session_state.get("new_file", False):
        st.subheader("Create New File")

        new_file_name = st.text_input("Enter new file name")
        new_file_name = (
            new_file_name + ".txt"
            if new_file_name and not new_file_name.endswith(".txt")
            else new_file_name
        )

        new_file_content = st.text_area("Enter file content", height=500)

        col1, col2, col3 = st.columns([1, 5, 1])
        with col1:
            if st.button("Save New File"):
                if new_file_name:
                    write_file(new_file_name, new_file_content)
                    st.success(f"File {new_file_name} added successfully")
                    st.session_state.new_file = False
                    st.rerun()
                else:
                    st.error("Please enter a file name")
        with col2:
            if st.button("Cancel"):
                st.session_state.new_file = False
                st.rerun()

    elif st.session_state.get("selected_file"):
        content = read_file(st.session_state.selected_file)

        if not is_edit_mode():
            # st.subheader("Viewing file")
            st.write(f"## {st.session_state.selected_file}")

            content_container = st.container()
            content_container.write(
                content,
                # f"""
                #     <div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; background-color: #f9f9f9;">
                #         <pre style="white-space: pre-wrap; word-wrap: break-word;">{content}</pre>
                #     </div>
                #     """,
                unsafe_allow_html=True,
            )

            st.write("")
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("Edit"):
                    enter_edit_mode()
                    st.rerun()

            with col3:
                if st.button("Delete File", type="primary"):
                    st.session_state["delete_file_button_clicked"] = True

                if st.session_state.get("delete_file_button_clicked", False):
                    st.warning("Are you sure you want to delete this file?")
                    st.button(
                        "Yes, I'm sure",
                        on_click=lambda: delete_file(st.session_state.selected_file),
                    )
                    st.button(
                        "No, don't delete it",
                        on_click=lambda: setattr(
                            st.session_state, "delete_file_button_clicked", False
                        ),
                    )

        else:
            st.subheader("Editing file")
            new_file_name = st.text_input(
                "File name", value=st.session_state.selected_file
            )
            new_file_name = (
                new_file_name + ".txt"
                if new_file_name and not new_file_name.endswith(".txt")
                else new_file_name
            )
            edited_content = st.text_area(
                "Edit file content", value=content, height=500
            )

            st.write("")
            col1, col3 = st.columns([1, 1])

            with col1:
                if st.button("Save Changes"):
                    if new_file_name != st.session_state.selected_file:
                        write_file(new_file_name, edited_content)
                        delete_file(st.session_state.selected_file)
                    else:
                        write_file(new_file_name, edited_content)

                    st.success("Changes saved successfully")
                    st.session_state.edit_mode = False
                    st.rerun()
            with col3:
                if st.button("Cancel"):
                    st.session_state.edit_mode = False
                    st.rerun()

    else:
        st.info("Select a file from the sidebar or create a new file to get started.")

    # CSS to style the delete button and adjust layout
    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: red;
            color: white;
        }
        .stButton {
            display: inline-block;
            margin-right: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
