from dataclasses import dataclass
from enum import Enum
from flask import url_for
from typing import Optional

from app.errors import LinkException
from app.models import User, Partner
from app.partner.partner_client import PartnerClient, PartnerUser
from app.account_linking import (
    process_login_case,
    process_link_case,
    PartnerLinkRequest,
)


class Action(Enum):
    Login = 1
    Link = 2


@dataclass
class PartnerCallbackResult:
    redirect_to_login: bool
    flash_message: Optional[str]
    flash_category: Optional[str]
    redirect: Optional[str]
    user: Optional[User]


def generate_account_not_allowed_to_log_in(partner_name: str) -> PartnerCallbackResult:
    return PartnerCallbackResult(
        redirect_to_login=True,
        flash_message=f"此帐户不允许使用{ partner_name }登录。请将您的帐户转换为完整的{ partner_name }帐户",
        flash_category="error",
        redirect=None,
        user=None,
    )


class PartnerCallbackHandler:
    def __init__(self, partner_client: PartnerClient):
        self.partner_client = partner_client

    def handle_login(self, partner: Partner) -> PartnerCallbackResult:
        try:
            user = self.__get_partner_user()
            if user is None:
                return generate_account_not_allowed_to_log_in()
            res = process_login_case(user, partner)
            return PartnerCallbackResult(
                redirect_to_login=False,
                flash_message=None,
                flash_category=None,
                redirect=None,
                user=res.user,
            )
        except LinkException as e:
            return PartnerCallbackResult(
                redirect_to_login=True,
                flash_message=e.message,
                flash_category="error",
                redirect=None,
                user=None,
            )

    def handle_link(
        self,
        current_user: Optional[User],
        partner: Partner,
    ) -> PartnerCallbackResult:
        if current_user is None:
            raise Exception("无法将当前用户和None的帐户链接起来")
        try:
            user = self.__get_partner_user()
            if user is None:
                return generate_account_not_allowed_to_log_in()
            res = process_link_case(user, current_user, partner)
            return PartnerCallbackResult(
                redirect_to_login=False,
                flash_message="账户关联成功",
                flash_category="success",
                redirect=url_for("dashboard.setting"),
                user=res.user,
            )
        except LinkException as e:
            return PartnerCallbackResult(
                redirect_to_login=False,
                flash_message=e.message,
                flash_category="error",
                redirect=None,
                user=None,
            )

    def __get_partner_user(self) -> Optional[PartnerLinkRequest]:
        partner_user = self.__get_user()
        if partner_user is None:
            return None
        return PartnerLinkRequest(
            email=partner_user.email,
            external_user_id=partner_user.id,
            name=partner_user.name,
            plan=partner_user.plan,
            from_partner=False,  # The user has started this flow, so we don't mark it as created by a partner
        )

    def __get_user(self) -> Optional[PartnerUser]:
        user = self.partner_client.get_user()
        if user is None:
            return None
        return PartnerUser(email=user.email, plan=user.plan, name=user.name, id=user.id)
