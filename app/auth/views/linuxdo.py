import requests
from flask import request, session, redirect, flash, url_for
from flask_limiter.util import get_remote_address
from flask_login import current_user
from requests_oauthlib import OAuth2Session
from typing import Optional

from app.auth.base import auth_bp
from app.auth.views.login_utils import after_login
from app.config import (
    URL,
    LINUXDO_CLIENT_ID,
    LINUXDO_CLIENT_SECRET,
)
from app.log import LOG
from app.models import ApiKey, User
from app.partner.partner_callback_handler import (
    PartnerCallbackHandler,
    Action,
)
from app.partner.partner_client import HttpPartnerClient
from app.partner.partner import get_partner_by_name
from app.utils import sanitize_next_url, sanitize_scheme

_authorization_base_url = "https://connect.linux.do/oauth2/authorize"
_token_url = "https://connect.linux.do/oauth2/token"

_scope = "all"
_user = "https://connect.linux.do/api/user"

# need to set explicitly redirect_uri instead of leaving the lib to pre-fill redirect_uri
# when served behind nginx, the redirect_uri is localhost... and not the real url
_redirect_uri = URL + "/auth/linuxdo/callback"

SESSION_ACTION_KEY = "oauth_action"
SESSION_STATE_KEY = "oauth_state"
DEFAULT_SCHEME = "auth.simplelogin"


def get_api_key_for_user(user: User) -> str:
    ak = ApiKey.create(
        user_id=user.id,
        name="Created via Login with Proton on mobile app",
        commit=True,
    )
    return ak.code


def extract_action() -> Optional[Action]:
    action = request.args.get("action")
    if action is not None:
        if action == "link":
            return Action.Link
        elif action == "login":
            return Action.Login
        else:
            LOG.w(f"Unknown action received: {action}")
            return None
    return Action.Login


def get_action_from_state() -> Action:
    oauth_action = session[SESSION_ACTION_KEY]
    if oauth_action == Action.Login.value:
        return Action.Login
    elif oauth_action == Action.Link.value:
        return Action.Link
    raise Exception(f"Unknown action in state: {oauth_action}")


@auth_bp.route("/linuxdo/login")
def linuxdo_login():
    if LINUXDO_CLIENT_ID is None or LINUXDO_CLIENT_SECRET is None:
        return redirect(url_for("auth.login"))

    action = extract_action()
    if action is None:
        return redirect(url_for("auth.login"))
    if action == Action.Link and not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    next_url = sanitize_next_url(request.args.get("next"))
    if next_url:
        session["oauth_next"] = next_url
    elif "oauth_next" in session:
        del session["oauth_next"]

    scheme = sanitize_scheme(request.args.get("scheme"))
    if scheme:
        session["oauth_scheme"] = scheme
    elif "oauth_scheme" in session:
        del session["oauth_scheme"]

    mode = request.args.get("mode", "session")
    if mode == "apikey":
        session["oauth_mode"] = "apikey"
    else:
        session["oauth_mode"] = "session"

    linuxdo = OAuth2Session(LINUXDO_CLIENT_ID, scope=_scope, redirect_uri=_redirect_uri)
    authorization_url, state = linuxdo.authorization_url(_authorization_base_url)

    # State is used to prevent CSRF, keep this for later.
    session[SESSION_STATE_KEY] = state
    session[SESSION_ACTION_KEY] = action.value
    return redirect(authorization_url)


@auth_bp.route("/linuxdo/callback")
def linuxdo_callback():
    if SESSION_STATE_KEY not in session or SESSION_STATE_KEY not in session:
        flash("Invalid state, please retry", "error")
        return redirect(url_for("auth.login"))
    if LINUXDO_CLIENT_ID is None or LINUXDO_CLIENT_SECRET is None:
        return redirect(url_for("auth.login"))

    # user clicks on cancel
    if "error" in request.args:
        flash("Please use another sign in method then", "warning")
        return redirect("/")

    linuxdo = OAuth2Session(
        LINUXDO_CLIENT_ID,
        scope="all",
        state=session[SESSION_STATE_KEY],
        redirect_uri=_redirect_uri,
    )

    def check_status_code(response: requests.Response) -> requests.Response:
        if response.status_code != 200:
            raise Exception(
                f"Bad Partner API response [status={response.status_code}]: {response.json()}"
            )
        return response

    linuxdo.register_compliance_hook("access_token_response", check_status_code)

    # headers = None

    try:
        token = linuxdo.fetch_token(
            _token_url,
            client_secret=LINUXDO_CLIENT_SECRET,
            authorization_response=request.url,
        )
        # {
        #     "access_token": "xxx",
        #     "expires_in": 3600,
        #     "refresh_token": "xxxx",
        #     "token_type": "bearer",
        #     "expires_at": 1743052334.0229573,
        # }

        # # Fetch a protected resource, i.e. user profile
        # {
        #     "id": 108990,
        #     "sub": "108990",
        #     "username": "yuanyou",
        #     "login": "yuanyou",
        #     "name": "原邮邮箱",
        #     "email": "u108990@linux.do",
        #     "avatar_template": "https://linux.do/user_avatar/linux.do/yuanyou/288/499808_2.png",
        #     "avatar_url": "https://linux.do/user_avatar/linux.do/yuanyou/288/499808_2.png",
        #     "active": True,
        #     "trust_level": 1,
        #     "silenced": False,
        #     "external_ids": None,
        #     "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        # }
    except Exception as e:
        LOG.warning(f"Error fetching Partner token: {e}")
        flash("There was an error in the login process", "error")
        return redirect(url_for("auth.login"))

    credentials = token["access_token"]
    action = get_action_from_state()

    linuxdo_client = HttpPartnerClient(_user, credentials, get_remote_address())
    handler = PartnerCallbackHandler(linuxdo_client)

    linuxdo_partner = get_partner_by_name("linuxdo")
    # LOG.debug(f"token is {token}")
    next_url = session.get("oauth_next")
    if action == Action.Login:
        res = handler.handle_login(linuxdo_partner)
    elif action == Action.Link:
        res = handler.handle_link(current_user, linuxdo_partner)
    else:
        raise Exception(f"Unknown Action: {action.name}")

    if res.flash_message is not None:
        flash(res.flash_message, res.flash_category)

    oauth_scheme = session.get("oauth_scheme")
    if session.get("oauth_mode", "session") == "apikey":
        apikey = get_api_key_for_user(res.user)
        scheme = oauth_scheme or DEFAULT_SCHEME
        return redirect(f"{scheme}:///login?apikey={apikey}")

    if res.redirect_to_login:
        return redirect(url_for("auth.login"))

    if next_url and next_url[0] == "/" and oauth_scheme:
        next_url = f"{oauth_scheme}://{next_url}"

    redirect_url = next_url or res.redirect
    return after_login(res.user, redirect_url, login_from_proton=True)
