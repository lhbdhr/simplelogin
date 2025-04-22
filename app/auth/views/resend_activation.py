from flask import request, flash, render_template, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, validators

from app.auth.base import auth_bp
from app.auth.views.register import send_activation_email
from app.extensions import limiter
from app.log import LOG
from app.models import User
from app.utils import sanitize_email, canonicalize_email


class ResendActivationForm(FlaskForm):
    email = StringField("Email", validators=[validators.DataRequired()])


@auth_bp.route("/resend_activation", methods=["GET", "POST"])
@limiter.limit("10/hour")
def resend_activation():
    form = ResendActivationForm(request.form)

    if form.validate_on_submit():
        email = sanitize_email(form.email.data)
        canonical_email = canonicalize_email(email)
        user = User.get_by(email=email) or User.get_by(email=canonical_email)

        if not user:
            flash("没有这样的电子邮件", "warning")
            return render_template("auth/resend_activation.html", form=form)

        if user.activated:
            flash("您的账户已激活，请登录", "success")
            return redirect(url_for("auth.login"))

        # user is not activated
        LOG.d("user %s is not activated", user)
        flash(
            "激活邮件已发送给您。请检查您的收件箱/垃圾邮件文件夹。",
            "warning",
        )
        send_activation_email(user, request.args.get("next"))
        return render_template("auth/register_waiting_activation.html")

    return render_template("auth/resend_activation.html", form=form)
