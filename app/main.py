import os
from loguru import logger
from dotenv import load_dotenv
import requests
from auth_utils import (
    handle_authentication,
    handle_logout,
    get_user_details
)
from config import ENV_FILE_PATH, EXTERNAL_AUTH_PROVIDER_NAME, BACKEND_URL
from page.chat import chat_page
from page.product_knowledge import product_knowledge_page

import streamlit as st


load_dotenv(ENV_FILE_PATH)

def check_backend_health():
    url = f"{BACKEND_URL}/api/health"
    headers = {"x-api-key": os.getenv("BACKEND_API_KEY")}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Backend health check failed: {str(e)}")
        return False

def get_user_using_external_user_id(auth_user_id):
    url = (
        f"{BACKEND_URL}/api/users/external/{EXTERNAL_AUTH_PROVIDER_NAME}/{auth_user_id}"
    )
    headers = {"x-api-key": os.getenv("BACKEND_API_KEY")}
    response = requests.get(url, headers=headers, timeout=30)
    st.session_state["user"] = response.json()
    logger.info(f"User response: {response.json()}")
    return response.json()

def get_user(user_id):
    url = f"{BACKEND_URL}/api/users/{user_id}"
    headers = {"x-api-key": os.getenv("BACKEND_API_KEY")}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:
        st.error(f"User {user_id} not found")
        st.stop()
    return response.json()

def get_user_tenents(user_id):
    
    if st.session_state.get("user") is None:
        user = get_user(user_id)
        st.session_state["user"] = user
    
    url = f"{BACKEND_URL}/api/tenants/{user_id}/tenants"
    headers = {"x-api-key": os.getenv("BACKEND_API_KEY")}
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:
        if response.json().get("detail") == "no tenants not found":
            st.error(f"Sorry but {st.session_state['user'].get('email')} is not a member of any tenant, please contact your admin to get you access!")
            st.stop()
    
    return response.json()

def sidebar_base_components():
    with st.sidebar:
        user_details = get_user_details(st.session_state.access_token)
        logger.info(f"User details: {user_details}")
        user_name = user_details.get("first_name", "User") + " " + user_details.get("last_name", "")
        st.session_state["auth_user_info"] = user_details
        
        user = get_user_using_external_user_id(user_details.get("id"))
        if user is None:
            st.error("User not found")
        tenants = get_user_tenents(user.get("id"))
        
        if len(tenants) == 0:
            st.error(f"Sorry but {user.get('email')} is not a member of any tenant, please contact your admin to get you access!")
            st.stop()
        else:
            st.session_state["tenants"] = tenants
        
        with st.expander(user_name):
            if st.button("Logout"):
                handle_logout()
        selected_tenant = st.session_state.get("selected_tenant")
        
        if selected_tenant is None and len(tenants) > 0:
            selected_tenant = tenants[0]
            st.session_state["selected_tenant"] = selected_tenant
            st.session_state["selected_tenant_id"] = selected_tenant.get("id")
            
        with st.expander("Select Tenant" if selected_tenant is None else f"{selected_tenant.get('name')}"):
            
            if len(tenants) == 1:
                selected_tenant = tenants[0]
                logger.info(f"Selected tenant: {selected_tenant}")
                st.session_state["selected_tenant"] = selected_tenant
                st.session_state["selected_tenant_id"] = selected_tenant.get("id")
                st.write("You are a member of only one tenant, so we selected it for you!")
                
            else:   
                options = [tenant.get("name") for tenant in tenants]    
                selected_tenant_str = st.selectbox("Please select a tenant", options)
                
                # find the tenant object from the name
                for tenant in tenants:
                    if tenant.get("name") == selected_tenant_str:
                        selected_tenant = tenant
                        st.session_state["selected_tenant"] = selected_tenant
                        st.session_state["selected_tenant_id"] = selected_tenant.get("id")


def main():
    
    logger.debug("Checking backend health...")
    if not check_backend_health():
        st.error("API service is afficted, please try again later!")
        st.stop()
    
    is_authenticated = handle_authentication()
    st.logo("images/pragmaticai_logo.png")

    with open("style.css", encoding="utf-8") as f:
        style_main = f.read()
    
    st.markdown(
        f"<style>{style_main}</style>",
        unsafe_allow_html=True,
    )
    
    if is_authenticated:
        sidebar_base_components()
                            
    # Define available pages
    pages = {
        # "Home": home_page,
        "Chat": chat_page,
        "Product Knowledge": product_knowledge_page,
    }
    # Page selection in sidebar
    with st.sidebar:
        # st.markdown("<div class='custom-radio-container'>", unsafe_allow_html=True)
        selected_page = st.radio("pages", list(pages.keys()))
        st.write("---")
        # st.markdown("</div>", unsafe_allow_html=True)
    # Load the selected page
    if selected_page:
        pages[selected_page]()
    else:
        chat_page()  # Default to chat page if no selection
    


if __name__ == "__main__":
    main()
