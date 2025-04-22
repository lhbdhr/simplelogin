import re2 as re
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.dashboard.base import dashboard_bp
from app.db import Session
from app.models import Referral, Payout

_REFERRAL_PATTERN = r"[0-9a-z-_]{3,}"


@dashboard_bp.route("/referral", methods=["GET", "POST"])
@login_required
def referral_route():
    if request.method == "POST":
        if request.form.get("form-name") == "create":
            code = request.form.get("code")
            if re.fullmatch(_REFERRAL_PATTERN, code) is None:
                flash(
                    "至少 3 个字符。仅限小写字母， "
                    "目前支持数字、破折号 (-) 和下划线 (_)。",
                    "error",
                )
                return redirect(url_for("dashboard.referral_route"))

            if Referral.get_by(code=code):
                flash("代码已被使用", "error")
                return redirect(url_for("dashboard.referral_route"))

            name = request.form.get("name")
            referral = Referral.create(user_id=current_user.id, code=code, name=name)
            Session.commit()
            flash("已创建新的推荐代码", "success")
            return redirect(
                url_for("dashboard.referral_route", highlight_id=referral.id)
            )
        elif request.form.get("form-name") == "update":
            referral_id = request.form.get("referral-id")
            referral = Referral.get(referral_id)
            if referral and referral.user_id == current_user.id:
                referral.name = request.form.get("name")
                Session.commit()
                flash("推荐人姓名已更新", "success")
                return redirect(
                    url_for("dashboard.referral_route", highlight_id=referral.id)
                )
        elif request.form.get("form-name") == "delete":
            referral_id = request.form.get("referral-id")
            referral = Referral.get(referral_id)
            if referral and referral.user_id == current_user.id:
                Referral.delete(referral.id)
                Session.commit()
                flash("已删除推荐", "success")
                return redirect(url_for("dashboard.referral_route"))

    # Highlight a referral
    highlight_id = request.args.get("highlight_id")
    if highlight_id:
        highlight_id = int(highlight_id)

    referrals = Referral.filter_by(user_id=current_user.id).all()
    # make sure the highlighted referral is the first referral
    highlight_index = None
    for ix, referral in enumerate(referrals):
        if referral.id == highlight_id:
            highlight_index = ix
            break

    if highlight_index:
        referrals.insert(0, referrals.pop(highlight_index))

    payouts = Payout.filter_by(user_id=current_user.id).all()

    return render_template("dashboard/referral.html", **locals())
