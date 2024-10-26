import os
from loguru import logger
from kinde_sdk import Configuration
from kinde_sdk.kinde_api_client import KindeApiClient, GrantType
from dotenv import load_dotenv
import requests
from urllib.parse import urlencode
import streamlit as st

load_dotenv(".env")

# Kinde configuration
KINDE_ISSUER_URL = "https://pragmaticai.kinde.com"
KINDE_CALLBACK_URL = "http://localhost:8501"
KINDE_CLIENT_ID = os.getenv("KINDE_CLIENT_ID")
KINDE_CLIENT_SECRET = os.getenv("KINDE_CLIENT_SECRET")

# Initialize Kinde client with configuration
configuration = Configuration(host=KINDE_ISSUER_URL)
kinde_api_client_params = {
    "configuration": configuration,
    "domain": KINDE_ISSUER_URL,
    "client_id": KINDE_CLIENT_ID,
    "client_secret": KINDE_CLIENT_SECRET,
    "grant_type": GrantType.AUTHORIZATION_CODE_WITH_PKCE,
    "callback_url": KINDE_CALLBACK_URL,
    "code_verifier": os.getenv("KINDE_CODE_VERIFIER"),
}

# Add this constant for the logout redirect URL
LOGOUT_REDIRECT_URL = "http://localhost:8501"  # Adjust this to your Streamlit app's URL


def get_login_url():
    kinde_client = KindeApiClient(**kinde_api_client_params)
    login_url = kinde_client.get_login_url() + "&" + "audience=api.pragmaticai.dev"
    logger.warning(f"Login URL: {login_url}")
    return login_url


def get_user_details(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{KINDE_ISSUER_URL}/oauth2/user_profile", headers=headers)
    return response.json() if response.status_code == 200 else None


def get_logout_url():
    kinde_client = KindeApiClient(**kinde_api_client_params)
    kinde_client.logout(redirect_to=LOGOUT_REDIRECT_URL)

    return LOGOUT_REDIRECT_URL


def handle_authentication():

    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None

    if "access_token" in st.session_state and st.session_state.access_token is not None:
        logger.info(f"Access token: ...{st.session_state.access_token[-10:]}")
    # Handle the callback
    query_params = st.query_params

    if "code" in query_params and not st.session_state.access_token:
        logger.info(
            "Access token is None, and code is in query params, fetching token..."
        )
        kinde_client = KindeApiClient(**kinde_api_client_params)
        st.session_state.kinde_client = kinde_client

        try:
            kinde_client.fetch_token(
                authorization_response=KINDE_CALLBACK_URL
                + "?"
                + urlencode(query_params)
            )

            access_token_object = kinde_client.__dict__.get(
                "_KindeApiClient__access_token_obj"
            )
            access_token = access_token_object.get("access_token")
            st.session_state.access_token = access_token
            st.rerun()
        except Exception as e:
            st.error(f"Error fetching token: {str(e)}")

    if st.session_state.access_token:
        return True
    else:
        login_url = get_login_url()
        # go to the login url
        logger.info(f"Redirecting to login URL: {login_url}")
        st.session_state["user_logged_out"] = True
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={login_url}">',
            unsafe_allow_html=True,
        )
        st.stop()


def handle_logout():
    logger.info("Handling logout")
    if (
        st.session_state.access_token
        and st.session_state.get("kinde_client") is not None
    ):
        st.session_state.access_token = None
        kinde_client = st.session_state.get("kinde_client")
        logout_url = kinde_client.logout(redirect_to=LOGOUT_REDIRECT_URL)
        st.session_state.pop("kinde_client")
        st.markdown(
            f'<meta http-equiv="refresh" content="0;url={logout_url}">',
            unsafe_allow_html=True,
        )
