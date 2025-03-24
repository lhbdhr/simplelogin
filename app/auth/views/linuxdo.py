from flask import request, session, redirect, flash
from requests_oauthlib import OAuth2Session

from app import s3
from app.auth.base import auth_bp
from app.config import URL, LINUXDO_CLIENT_ID, LINUXDO_CLIENT_SECRET
from psycopg2.errors import UniqueViolation
from app.models import PartnerUser
from app.auth.partner import get_partner_by_name
import sqlalchemy.exc

from app.db import Session
from app.log import LOG
from app.models import User, File, SocialAuth
from app.utils import random_string, sanitize_email, sanitize_next_url
from .login_utils import after_login

_authorization_base_url = "https://connect.linux.do/oauth2/authorize"
_token_url = "https://connect.linux.do/oauth2/token"

_scope = "all"
_user = "https://connect.linux.do/api/user"

# need to set explicitly redirect_uri instead of leaving the lib to pre-fill redirect_uri
# when served behind nginx, the redirect_uri is localhost... and not the real url
_redirect_uri = URL + "/auth/linuxdo/callback"


@auth_bp.route("/linuxdo/login")
def linuxdo_login():
    # to avoid flask-login displaying the login error message
    session.pop("_flashes", None)

    next_url = sanitize_next_url(request.args.get("next"))

    # Google does not allow to append param to redirect_url
    # we need to pass the next url by session
    if next_url:
        session["linuxdo_next_url"] = next_url

    google = OAuth2Session(LINUXDO_CLIENT_ID, scope=_scope, redirect_uri=_redirect_uri)
    authorization_url, state = google.authorization_url(_authorization_base_url)

    # State is used to prevent CSRF, keep this for later.
    session["oauth_state"] = state
    return redirect(authorization_url)


@auth_bp.route("/linuxdo/callback")
def linuxdo_callback():
    LOG.d("linuxdo callback")
    # user clicks on cancel
    if "error" in request.args:
        flash("please use another sign in method then", "warning")
        return redirect("/")

    linuxdo = OAuth2Session(
        LINUXDO_CLIENT_ID,
        # some how Google Login fails with oauth_state KeyError
        # state=session["oauth_state"],
        scope="all",
        redirect_uri=_redirect_uri,
    )
    linuxdo.fetch_token(
        _token_url,
        client_secret=LINUXDO_CLIENT_SECRET,
        authorization_response=request.url,
    )
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
    linuxdo_user_data = linuxdo.get("https://connect.linux.do/api/user").json()
    # LOG.d("linuxdo user data %s", linuxdo_user_data)

    email = sanitize_email(linuxdo_user_data["email"])
    user = User.get_by(email=email)

    name = linuxdo_user_data.get("name")
    picture_url = linuxdo_user_data.get("avatar_url")
    id = linuxdo_user_data.get("id")

    if user:
        if picture_url and not user.profile_picture_id:
            LOG.d("set user profile picture to %s", picture_url)
            file = create_file_from_url(user, picture_url)
            user.profile_picture_id = file.id
            Session.commit()
    else:
        try:
            # user = User.create(email=email, name=name, activated=True)
            # Session.commit()
            partner = get_partner_by_name("linuxdo")
            user = User.create(
                email=email,
                name=name,
                activated=True,
                from_partner=True,
                flush=True,
            )
            PartnerUser.create(
                user_id=user.id,
                partner_id=partner.id,
                partner_email=email,
                external_user_id=id,
                flush=True,
            )
            Session.commit()
        except (UniqueViolation, sqlalchemy.exc.IntegrityError) as e:
            Session.rollback()
            LOG.debug(f"Got the duplicate user error: {e}")
            return False

    next_url = None
    # The activation link contains the original page, for ex authorize page
    if "linuxdo_next_url" in session:
        next_url = session["linuxdo_next_url"]
        LOG.d("redirect user to %s", next_url)

        # reset the next_url to avoid user getting redirected at each login :)
        session.pop("linuxdo_next_url", None)

    if not SocialAuth.get_by(user_id=user.id, social="linuxdo"):
        SocialAuth.create(user_id=user.id, social="linuxdo")
        Session.commit()

    return after_login(user, next_url)


def create_file_from_url(user, url) -> File:
    file_path = random_string(30)
    file = File.create(path=file_path, user_id=user.id)

    s3.upload_from_url(url, file_path)

    Session.flush()
    LOG.d("upload file %s to s3", file)

    return file
