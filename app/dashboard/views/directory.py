from typing import Optional

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    validators,
    SelectMultipleField,
    BooleanField,
    IntegerField,
)

from app import parallel_limiter
from app.config import (
    EMAIL_DOMAIN,
    ALIAS_DOMAINS,
    MAX_NB_DIRECTORY,
    BOUNCE_PREFIX_FOR_REPLY_PHASE,
)
from app.dashboard.base import dashboard_bp
from app.db import Session
from app.errors import DirectoryInTrashError
from app.models import Directory, Mailbox, DirectoryMailbox
from app.user_audit_log_utils import emit_user_audit_log, UserAuditLogAction


class NewDirForm(FlaskForm):
    name = StringField(
        "name", validators=[validators.DataRequired(), validators.Length(min=3)]
    )


class ToggleDirForm(FlaskForm):
    directory_id = IntegerField(validators=[validators.DataRequired()])
    directory_enabled = BooleanField(validators=[])


class UpdateDirForm(FlaskForm):
    directory_id = IntegerField(validators=[validators.DataRequired()])
    mailbox_ids = SelectMultipleField(
        validators=[validators.DataRequired()], validate_choice=False, choices=[]
    )


class DeleteDirForm(FlaskForm):
    directory_id = IntegerField(validators=[validators.DataRequired()])


@dashboard_bp.route("/directory", methods=["GET", "POST"])
@login_required
@parallel_limiter.lock(only_when=lambda: request.method == "POST")
def directory():
    dirs = (
        Directory.filter_by(user_id=current_user.id)
        .order_by(Directory.created_at.desc())
        .all()
    )

    mailboxes = current_user.mailboxes()

    new_dir_form = NewDirForm()
    toggle_dir_form = ToggleDirForm()
    update_dir_form = UpdateDirForm()
    update_dir_form.mailbox_ids.choices = [
        (str(mailbox.id), str(mailbox.id)) for mailbox in mailboxes
    ]
    delete_dir_form = DeleteDirForm()

    if request.method == "POST":
        if request.form.get("form-name") == "delete":
            if not delete_dir_form.validate():
                flash("无效请求", "warning")
                return redirect(url_for("dashboard.directory"))
            dir_obj: Optional[Directory] = Directory.get(
                delete_dir_form.directory_id.data
            )

            if not dir_obj:
                flash("未知错误。请刷新页面", "warning")
                return redirect(url_for("dashboard.directory"))
            elif dir_obj.user_id != current_user.id:
                flash("您不能删除此目录", "warning")
                return redirect(url_for("dashboard.directory"))

            name = dir_obj.name
            emit_user_audit_log(
                user=current_user,
                action=UserAuditLogAction.DeleteDirectory,
                message=f"Delete directory {dir_obj.id} ({dir_obj.name})",
            )
            Directory.delete(dir_obj.id)
            Session.commit()
            flash(f"目录 {name} 已删除", "success")

            return redirect(url_for("dashboard.directory"))

        if request.form.get("form-name") == "toggle-directory":
            if not toggle_dir_form.validate():
                flash("无效请求", "warning")
                return redirect(url_for("dashboard.directory"))
            dir_id = toggle_dir_form.directory_id.data
            dir_obj: Optional[Directory] = Directory.get(dir_id)

            if not dir_obj or dir_obj.user_id != current_user.id:
                flash("未知错误。请刷新页面", "warning")
                return redirect(url_for("dashboard.directory"))

            if toggle_dir_form.directory_enabled.data:
                dir_obj.disabled = False
                flash(f"自动创建已为 {dir_obj.name} 启用", "success")
            else:
                dir_obj.disabled = True
                flash(f"自动创建已为 {dir_obj.name} 禁用", "warning")

            emit_user_audit_log(
                user=current_user,
                action=UserAuditLogAction.UpdateDirectory,
                message=f"Updated directory {dir_obj.id} ({dir_obj.name}) set disabled = {dir_obj.disabled}",
            )
            Session.commit()

            return redirect(url_for("dashboard.directory"))

        elif request.form.get("form-name") == "update":
            if not update_dir_form.validate():
                flash("无效请求", "warning")
                return redirect(url_for("dashboard.directory"))
            dir_id = update_dir_form.directory_id.data
            dir_obj: Optional[Directory] = Directory.get(dir_id)

            if not dir_obj or dir_obj.user_id != current_user.id:
                flash("未知错误。请刷新页面", "warning")
                return redirect(url_for("dashboard.directory"))

            mailbox_ids = update_dir_form.mailbox_ids.data
            # check if mailbox is not tempered with
            mailboxes = []
            for mailbox_id in mailbox_ids:
                mailbox = Mailbox.get(mailbox_id)
                if (
                    not mailbox
                    or mailbox.user_id != current_user.id
                    or not mailbox.verified
                ):
                    flash("出了点问题，请重试", "warning")
                    return redirect(url_for("dashboard.directory"))
                mailboxes.append(mailbox)

            if not mailboxes:
                flash("您必须至少选择 1 个邮箱", "warning")
                return redirect(url_for("dashboard.directory"))

            # first remove all existing directory-mailboxes links
            DirectoryMailbox.filter_by(directory_id=dir_obj.id).delete()
            Session.flush()

            for mailbox in mailboxes:
                DirectoryMailbox.create(directory_id=dir_obj.id, mailbox_id=mailbox.id)

            mailboxes_as_str = ",".join(map(str, mailbox_ids))
            emit_user_audit_log(
                user=current_user,
                action=UserAuditLogAction.UpdateDirectory,
                message=f"Updated directory {dir_obj.id} ({dir_obj.name}) mailboxes ({mailboxes_as_str})",
            )
            Session.commit()
            flash(f"目录 {dir_obj.name} 已更新", "success")

            return redirect(url_for("dashboard.directory"))
        elif request.form.get("form-name") == "create":
            if not current_user.is_premium():
                flash("只有高级计划可以添加目录", "warning")
                return redirect(url_for("dashboard.directory"))

            if current_user.directory_quota <= 0:
                flash(
                    f"目录数量不能超过 {MAX_NB_DIRECTORY} 个",
                    "warning",
                )
                return redirect(url_for("dashboard.directory"))

            if new_dir_form.validate():
                new_dir_name = new_dir_form.name.data.lower()

                if Directory.get_by(name=new_dir_name):
                    flash(f"{new_dir_name} 已经被使用", "warning")
                elif new_dir_name in (
                    "reply",
                    "ra",
                    "bounces",
                    "bounce",
                    "transactional",
                    BOUNCE_PREFIX_FOR_REPLY_PHASE,
                ):
                    flash(
                        "此目录名称已被保留，请选择其他名称",
                        "warning",
                    )
                else:
                    try:
                        new_dir = Directory.create(
                            name=new_dir_name, user_id=current_user.id
                        )
                        emit_user_audit_log(
                            user=current_user,
                            action=UserAuditLogAction.CreateDirectory,
                            message=f"New directory {new_dir.name} ({new_dir.name})",
                        )
                    except DirectoryInTrashError:
                        flash(
                            f"{new_dir_name} 之前已被使用，无法重复使用",
                            "error",
                        )
                    else:
                        Session.commit()
                        mailbox_ids = request.form.getlist("mailbox_ids")
                        if mailbox_ids:
                            # check if mailbox is not tempered with
                            mailboxes = []
                            for mailbox_id in mailbox_ids:
                                mailbox = Mailbox.get(mailbox_id)
                                if (
                                    not mailbox
                                    or mailbox.user_id != current_user.id
                                    or not mailbox.verified
                                ):
                                    flash("出了点问题，请重试", "warning")
                                    return redirect(url_for("dashboard.directory"))
                                mailboxes.append(mailbox)

                            for mailbox in mailboxes:
                                DirectoryMailbox.create(
                                    directory_id=new_dir.id, mailbox_id=mailbox.id
                                )

                            Session.commit()

                        flash(f"目录 {new_dir.name} 已创建", "success")

                    return redirect(url_for("dashboard.directory"))

    return render_template(
        "dashboard/directory.html",
        dirs=dirs,
        toggle_dir_form=toggle_dir_form,
        update_dir_form=update_dir_form,
        delete_dir_form=delete_dir_form,
        new_dir_form=new_dir_form,
        mailboxes=mailboxes,
        EMAIL_DOMAIN=EMAIL_DOMAIN,
        ALIAS_DOMAINS=ALIAS_DOMAINS,
    )
