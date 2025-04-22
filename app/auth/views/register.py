import requests
from flask import request, flash, render_template, redirect, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, validators

from app import email_utils, config
from app.auth.base import auth_bp
from app.config import CONNECT_WITH_PROTON, CONNECT_WITH_OIDC_ICON
from app.auth.views.login_utils import get_referral
from app.config import URL, HCAPTCHA_SECRET, HCAPTCHA_SITEKEY
from app.db import Session
from app.email_utils import (
    email_can_be_used_as_mailbox,
    personal_email_already_used,
)
from app.events.auth_event import RegisterEvent
from app.log import LOG
from app.models import User, ActivationCode, DailyMetric
from app.utils import random_string, encode_url, sanitize_email, canonicalize_email


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[validators.DataRequired()])
    password = StringField(
        "Password",
        validators=[validators.DataRequired(), validators.Length(min=8, max=100)],
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        LOG.d("user is already authenticated, redirect to dashboard")
        flash("您已登录", "warning")
        return redirect(url_for("dashboard.index"))

    if config.DISABLE_REGISTRATION:
        flash("注册已关闭", "error")
        return redirect(url_for("auth.login"))

    form = RegisterForm(request.form)
    next_url = request.args.get("next")

    if form.validate_on_submit():
        # only check if hcaptcha is enabled
        if HCAPTCHA_SECRET:
            # check with hCaptcha
            token = request.form.get("h-captcha-response")
            params = {"secret": HCAPTCHA_SECRET, "response": token}
            hcaptcha_res = requests.post(
                "https://hcaptcha.com/siteverify", data=params
            ).json()
            # return something like
            # {'success': True,
            #  'challenge_ts': '2020-07-23T10:03:25',
            #  'hostname': '127.0.0.1'}
            if not hcaptcha_res["success"]:
                LOG.w(
                    "User put wrong captcha %s %s",
                    form.email.data,
                    hcaptcha_res,
                )
                flash("验证码错误", "error")
                RegisterEvent(RegisterEvent.ActionType.catpcha_failed).send()
                return render_template(
                    "auth/register.html",
                    form=form,
                    next_url=next_url,
                    HCAPTCHA_SITEKEY=HCAPTCHA_SITEKEY,
                )

        email = canonicalize_email(form.email.data)
        if not email_can_be_used_as_mailbox(email):
            flash("您不能将此电子邮箱地址用作您的个人收件箱。", "error")
            RegisterEvent(RegisterEvent.ActionType.email_in_use).send()
        else:
            sanitized_email = sanitize_email(form.email.data)
            if personal_email_already_used(email) or personal_email_already_used(
                sanitized_email
            ):
                flash(f"电子邮箱地址 {email} 已被使用", "error")
                RegisterEvent(RegisterEvent.ActionType.email_in_use).send()
            else:
                LOG.d("create user %s", email)
                user = User.create(
                    email=email,
                    name=form.email.data,
                    password=form.password.data,
                    referral=get_referral(),
                )
                Session.commit()

                try:
                    send_activation_email(user, next_url)
                    RegisterEvent(RegisterEvent.ActionType.success).send()
                    DailyMetric.get_or_create_today_metric().nb_new_web_non_proton_user += 1
                    Session.commit()
                except Exception:
                    flash("电子邮件无效，您确定该电子邮件正确吗？", "error")
                    RegisterEvent(RegisterEvent.ActionType.invalid_email).send()
                    return redirect(url_for("auth.register"))

                return render_template("auth/register_waiting_activation.html")

    return render_template(
        "auth/register.html",
        form=form,
        next_url=next_url,
        HCAPTCHA_SITEKEY=HCAPTCHA_SITEKEY,
        connect_with_proton=CONNECT_WITH_PROTON,
        connect_with_oidc=config.OIDC_CLIENT_ID is not None,
        connect_with_oidc_icon=CONNECT_WITH_OIDC_ICON,
    )


def send_activation_email(user, next_url):
    # the activation code is valid for 1h and delete all previous codes
    Session.query(ActivationCode).filter(ActivationCode.user_id == user.id).delete()
    activation = ActivationCode.create(user_id=user.id, code=random_string(30))
    Session.commit()

    # Send user activation email
    activation_link = f"{URL}/auth/activate?code={activation.code}"
    if next_url:
        LOG.d("redirect user to %s after activation", next_url)
        activation_link = activation_link + "&next=" + encode_url(next_url)

    email_utils.send_activation_email(user, activation_link)
