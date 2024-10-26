import os
from typing import Union
from fastapi import FastAPI, Depends, HTTPException, status, Request, APIRouter
from fastapi.responses import RedirectResponse
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware
from kinde_sdk import Configuration
from kinde_sdk.kinde_api_client import KindeApiClient, GrantType
from dotenv import load_dotenv

load_dotenv("../.env")


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("KINDE_CODE_VERIFIER"))

# Callback endpoint
router = APIRouter()

# Initialize Kinde client with configuration
configuration = Configuration(host=os.getenv("KINDE_ISSUER_URL"))

SITE_URL = "http://localhost:6969"
LOGOUT_REDIRECT_URL = "http://localhost:6969/api/auth/logout"
KINDE_CALLBACK_URL = "http://localhost:6969/api/auth/kinde_callback"
KINDE_ISSUER_URL = "https://pragmaticai.kinde.com"


kinde_api_client_params = {
    "configuration": configuration,
    "domain": KINDE_ISSUER_URL,
    "client_id": os.getenv("KINDE_CLIENT_ID"),
    "client_secret": os.getenv("KINDE_CLIENT_SECRET"),
    "grant_type": GrantType.AUTHORIZATION_CODE_WITH_PKCE,
    "callback_url": KINDE_CALLBACK_URL,
}
if kinde_api_client_params.get("grant_type") == GrantType.AUTHORIZATION_CODE_WITH_PKCE:
    kinde_api_client_params["code_verifier"] = os.getenv("KINDE_CODE_VERIFIER")

# User clients dictionary to store Kinde clients for each user
user_clients = {}


# Dependency to get the current user's KindeApiClient instance
def get_kinde_client(request: Request) -> KindeApiClient:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if user_id not in user_clients:
        # If the client does not exist, create a new instance with parameters
        user_clients[user_id] = KindeApiClient(**kinde_api_client_params)

    kinde_client = user_clients[user_id]
    # Ensure the client is authenticated
    if not kinde_client.is_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return kinde_client


# Login endpoint
@app.get("/api/auth/login")
def login(request: Request):
    kinde_client = KindeApiClient(**kinde_api_client_params)
    login_url = kinde_client.get_login_url()
    logger.info(f"Login URL: {login_url}")
    return RedirectResponse(login_url)


# Register endpoint
@app.get("/api/auth/register")
def register(request: Request):
    kinde_client = KindeApiClient(**kinde_api_client_params)
    register_url = kinde_client.get_register_url()
    return RedirectResponse(register_url)


@app.get("/api/auth/kinde_callback")
def callback(request: Request):
    kinde_client = KindeApiClient(**kinde_api_client_params)
    logger.info(f"Request URL: {request.url}")
    kinde_client.fetch_token(authorization_response=str(request.url))
    user = kinde_client.get_user_details()
    request.session["user_id"] = user.get("id")
    user_clients[user.get("id")] = kinde_client
    return RedirectResponse("/")


# Logout endpoint
@app.get("/api/auth/logout")
def logout(request: Request):
    user_id = request.session.get("user_id")
    if user_id in user_clients:
        kinde_client = user_clients[user_id]
        logout_url = kinde_client.logout(redirect_to=LOGOUT_REDIRECT_URL)
        del user_clients[user_id]
        request.session.pop("user_id", None)
        return RedirectResponse(logout_url)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )


@app.get("/")
def read_root(kinde_client: KindeApiClient = Depends(get_kinde_client)):
    print(kinde_client.get_user_details())
    # Now this route requires authentication
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fast_api:app", host="0.0.0.0", port=6969)
