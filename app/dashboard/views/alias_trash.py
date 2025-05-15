from flask import render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField

from app import alias_delete
from app.config import PAGE_LIMIT
from app.dashboard.base import dashboard_bp
from app.db import Session
from app.errors import CannotCreateAliasQuotaExceeded
from app.models import Alias


class SettingForm(FlaskForm):
    action = StringField("action")
    alias_id = IntegerField("alias-id")


@dashboard_bp.route("/alias_trash", methods=["GET", "POST"])
@login_required
def alias_trash():
    try:
        page = int(request.args.get("page", 0))
    except ValueError:
        page = 0

    form = SettingForm()
    if request.method == "POST":
        if not form.validate():
            flash("无效请求", "warning")
            return redirect(url_for("dashboard.alias_trash"))
        action = form.action.data.strip()
        if action == "trash-all":
            count = alias_delete.clear_trash(current_user)
            flash(f"{count} 个别名已永久删除", "success")
        elif action == "restore-one":
            try:
                alias_id = int(form.alias_id.data)
                try:
                    alias_delete.restore_alias(current_user, alias_id)
                    flash("已恢复别名", "success")
                except CannotCreateAliasQuotaExceeded:
                    flash("您的别名数量达到限额，无法恢复此别名", "error")
            except ValueError:
                flash("无效别名", "warning")
        elif action == "restore-all":
            try:
                count = alias_delete.restore_all_alias(current_user)
                flash(f"已恢复 {count} 个别名", "success")
            except CannotCreateAliasQuotaExceeded:
                flash("您的别名数量已达到限制，无法恢复所有别名", "error")

    alias_in_trash = (
        Session.query(Alias)
        .filter(Alias.user_id == current_user.id, Alias.delete_on != None)  # noqa: E711
        .order_by(Alias.delete_on.asc())
        .limit(PAGE_LIMIT)
        .offset(page * PAGE_LIMIT)
    ).all()
    alias_trash_count = (
        Session.query(Alias)
        .filter(Alias.user_id == current_user.id, Alias.delete_on != None)  # noqa: E711
        .count()
    )

    return render_template(
        "dashboard/alias_trash.html",
        alias_in_trash=alias_in_trash,
        alias_trash_count=alias_trash_count,
        page=page,
        last_page=len(alias_in_trash) < PAGE_LIMIT,
        form=form,
    )
