import arrow
from flask import render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user

from app import s3
from app.constants import JobType
from app.dashboard.base import dashboard_bp
from app.dashboard.views.enter_sudo import sudo_required
from app.db import Session
from app.extensions import limiter
from app.log import LOG
from app.models import File, BatchImport, Job
from app.utils import random_string, CSRFValidationForm


@dashboard_bp.route("/batch_import", methods=["GET", "POST"])
@login_required
@sudo_required
@limiter.limit("10/minute", methods=["POST"])
def batch_import_route():
    # only for users who have custom domains
    if not current_user.verified_custom_domains():
        flash("别名批量导入仅适用于自定义域", "warning")

    if current_user.disable_import:
        flash(
            "您无法使用导入功能，请联系我们以获取更多信息",
            "error",
        )
        return redirect(url_for("dashboard.index"))

    batch_imports = BatchImport.filter_by(
        user_id=current_user.id, processed=False
    ).all()

    csrf_form = CSRFValidationForm()

    if request.method == "POST":
        if not csrf_form.validate():
            flash("无效请求", "warning")
            return redirect(request.url)
        if len(batch_imports) > 10:
            flash(
                "您导入的内容已经过多。请等待部分内容清理完毕",
                "error",
            )
            return render_template(
                "dashboard/batch_import.html",
                batch_imports=batch_imports,
                csrf_form=csrf_form,
            )

        alias_file = request.files["alias-file"]

        file_path = random_string(20) + ".csv"
        file = File.create(user_id=current_user.id, path=file_path)
        s3.upload_from_bytesio(file_path, alias_file)
        Session.flush()
        LOG.d("upload file %s to s3 at %s", file, file_path)

        bi = BatchImport.create(user_id=current_user.id, file_id=file.id)
        Session.flush()
        LOG.d("Add a batch import job %s for %s", bi, current_user)

        # Schedule batch import job
        Job.create(
            name=JobType.BATCH_IMPORT.value,
            payload={"batch_import_id": bi.id},
            run_at=arrow.now(),
        )
        Session.commit()

        flash(
            "文件已成功上传，即将开始导入",
            "success",
        )

        return redirect(url_for("dashboard.batch_import_route"))

    return render_template(
        "dashboard/batch_import.html", batch_imports=batch_imports, csrf_form=csrf_form
    )
