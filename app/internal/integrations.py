from flask import make_response, redirect, url_for, flash
from flask_login import current_user

from .base import internal_bp


@internal_bp.route("/integrations/proton")
def set_enable_proton_cookie():
    if current_user.is_authenticated:
        redirect_url = url_for("dashboard.setting", _anchor="connect-with-proton")
    else:
        redirect_url = url_for("auth.login")

    response = make_response(redirect(redirect_url))

    flash("您现在可以连接您的 Proton 和您的 SimpleLogin 帐户", "success")
    return response
