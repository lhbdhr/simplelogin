from newrelic import agent

from app.db import Session
from app.events.event_dispatcher import EventDispatcher
from app.events.generated.event_pb2 import EventContent, UserUnlinked
from app.log import LOG
from app.models import User, PartnerUser
from app.partner.partner import get_partner_by_name
from app.user_audit_log_utils import emit_user_audit_log, UserAuditLogAction


def can_unlink_partner_account(user: User) -> bool:
    return (user.flags & User.FLAG_CREATED_FROM_PARTNER) == 0


def perform_partner_account_unlink(
    partner_name: str, current_user: User, skip_check: bool = False
) -> None | str:
    if not skip_check and not can_unlink_partner_account(current_user):
        return None
    partner = get_partner_by_name(partner_name)
    partner_user = PartnerUser.get_by(user_id=current_user.id, partner_id=partner.id)
    if partner_user is not None:
        LOG.info(f"User {current_user} has unlinked the account from {partner_user}")
        emit_user_audit_log(
            user=current_user,
            action=UserAuditLogAction.UnlinkAccount,
            message=f"User has unlinked the account (email={partner_user.partner_email} | external_user_id={partner_user.external_user_id})",
        )
        EventDispatcher.send_event(
            partner_user.user, EventContent(user_unlinked=UserUnlinked())
        )
        PartnerUser.delete(partner_user.id)
    external_user_id = partner_user.external_user_id
    Session.commit()
    agent.record_custom_event("AccountUnlinked", {"partner": partner.name})
    return external_user_id
