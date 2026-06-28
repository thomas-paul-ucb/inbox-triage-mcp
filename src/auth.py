"""
Handles OAuth 2.0 authentication for the Gmail MCP server.

First run: opens a browser for you to log in and grant access,
then saves the resulting tokens locally so future runs don't
need to repeat that step (until the token expires).
"""

import os
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/oauth2callback")

TOKEN_PATH = os.path.join("data", "token.json")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly"

# Holds the auth code once Google redirects back to our local server
_auth_code = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    """Tiny local server that catches Google's OAuth redirect."""

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        if "code" in query:
            _auth_code["code"] = query["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Login successful. You can close this tab.")
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # keep terminal output quiet


def _run_oauth_flow():
    """Opens the browser for the user to log in, then waits for the redirect."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_request_url = f"{AUTH_URL}?{urlencode(params)}"

    print("Opening browser for Google login...")
    webbrowser.open(auth_request_url)

    server = HTTPServer(("localhost", 8080), _CallbackHandler)
    server.handle_request()  # blocks until one request comes in

    return _auth_code.get("code")


def _exchange_code_for_tokens(code):
    response = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def get_access_token():
    """
    Returns a valid access token, running the OAuth flow if needed.

    NOTE: token refresh logic comes in a follow-up step -- for now
    this always runs a fresh login if no saved token exists.
    """
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            tokens = json.load(f)
        return tokens["access_token"]

    code = _run_oauth_flow()
    if not code:
        raise RuntimeError("OAuth flow did not return an authorization code.")

    tokens = _exchange_code_for_tokens(code)

    os.makedirs("data", exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        json.dump(tokens, f)

    return tokens["access_token"]