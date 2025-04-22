"""
Allow user to disable an alias or block a contact via the one click unsubscribe
"""

from app.db import Session


from flask import redirect, url_for, flash, request, render_template
from flask_login import login_required, current_user

from app import alias_utils
from app.dashboard.base import dashboard_bp
from app.handler.unsubscribe_encoder import UnsubscribeAction
from app.handler.unsubscribe_handler import UnsubscribeHandler
from app.models import Alias, Contact


@dashboard_bp.route("/unsubscribe/<int:alias_id>", methods=["GET", "POST"])
@login_required
def unsubscribe(alias_id):
    alias = Alias.get(alias_id)
    if not alias:
        flash("链接错误。请将您重定向至主页", "warning")
        return redirect(url_for("dashboard.index"))

    if alias.user_id != current_user.id:
        flash(
            "您无权访问此页面。请将您重定向至主页",
            "warning",
        )
        return redirect(url_for("dashboard.index"))

    # automatic unsubscribe, according to https://tools.ietf.org/html/rfc8058
    if request.method == "POST":
        alias_utils.change_alias_status(
            alias, enabled=False, message="Set enabled=False from unsubscribe request"
        )
        flash(f"别名 {alias.email} 已被屏蔽", "success")
        Session.commit()

        return redirect(url_for("dashboard.index", highlight_alias_id=alias.id))
    else:  # ask user confirmation
        return render_template("dashboard/unsubscribe.html", alias=alias.email)


@dashboard_bp.route("/block_contact/<int:contact_id>", methods=["GET", "POST"])
@login_required
def block_contact(contact_id):
    contact = Contact.get(contact_id)
    if not contact:
        flash("链接错误。请将您重定向至主页", "warning")
        return redirect(url_for("dashboard.index"))

    if contact.user_id != current_user.id:
        flash(
            "您无权访问此页面。请将您重定向至主页",
            "warning",
        )
        return redirect(url_for("dashboard.index"))

    # automatic unsubscribe, according to https://tools.ietf.org/html/rfc8058
    if request.method == "POST":
        contact.block_forward = True
        flash(f"从 {contact.website_email} 发送的电子邮件现已被屏蔽", "success")
        Session.commit()

        return redirect(
            url_for(
                "dashboard.alias_contact_manager",
                alias_id=contact.alias_id,
                highlight_contact_id=contact.id,
            )
        )
    else:  # ask user confirmation
        return render_template("dashboard/block_contact.html", contact=contact)


@dashboard_bp.route("/unsubscribe/encoded/<encoded_request>", methods=["GET"])
@login_required
def encoded_unsubscribe(encoded_request: str):
    unsub_data = UnsubscribeHandler().handle_unsubscribe_from_request(
        current_user, encoded_request
    )
    if not unsub_data:
        flash("无效的取消订阅请求", "error")
        return redirect(url_for("dashboard.index"))
    if unsub_data.action == UnsubscribeAction.DisableAlias:
        alias = Alias.get(unsub_data.data)
        flash(f"别名 {alias.email} 已被屏蔽", "success")
        return redirect(url_for("dashboard.index", highlight_alias_id=alias.id))
    if unsub_data.action == UnsubscribeAction.DisableContact:
        contact = Contact.get(unsub_data.data)
        flash(f"从 {contact.website_email} 发送的电子邮件现已被屏蔽", "success")
        return redirect(
            url_for(
                "dashboard.alias_contact_manager",
                alias_id=contact.alias_id,
                highlight_contact_id=contact.id,
            )
        )
    if unsub_data.action == UnsubscribeAction.UnsubscribeNewsletter:
        flash("您已取消订阅新闻通讯", "success")
        return redirect(
            url_for(
                "dashboard.index",
            )
        )
    if unsub_data.action == UnsubscribeAction.OriginalUnsubscribeMailto:
        flash("原取消订阅请求已转发", "success")
        return redirect(
            url_for(
                "dashboard.index",
            )
        )
    return redirect(url_for("dashboard.index"))
