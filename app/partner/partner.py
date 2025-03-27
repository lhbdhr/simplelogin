from typing import Dict

from app.db import Session
from app.errors import PartnerNotSetUp
from app.models import Partner

# 缓存多个合作伙伴
_PARTNER_CACHE: Dict[str, Partner] = {}


def get_partner_by_name(partner_name: str) -> Partner:
    """根据名称查询 Partner，使用缓存"""
    global _PARTNER_CACHE

    if partner_name in _PARTNER_CACHE:
        return _PARTNER_CACHE[partner_name]

    partner = Partner.get_by(name=partner_name)

    if partner is None:
        raise PartnerNotSetUp(f"Partner '{partner_name}' not found")

    # 将 Partner 加入缓存
    Session.expunge(partner)
    _PARTNER_CACHE[partner_name] = partner

    return partner
