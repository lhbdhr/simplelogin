from app.config import (
    ALIAS_DOMAINS,
    PREMIUM_ALIAS_DOMAINS,
    PROTON_CLIENT_ID,
    GITHUB_CLIENT_ID,
    GOOGLE_CLIENT_ID,
    LINUXDO_CLIENT_ID,
)
from app.db import Session
from app.log import LOG
from app.models import Mailbox, Contact, SLDomain, Partner
from app.pgp_utils import load_public_key
from app.proton.proton_partner import PROTON_PARTNER_NAME
from server import create_light_app


def load_pgp_public_keys():
    """Load PGP public key to keyring"""
    for mailbox in Mailbox.filter(Mailbox.pgp_public_key.isnot(None)).all():
        LOG.d("Load PGP key for mailbox %s", mailbox)
        fingerprint = load_public_key(mailbox.pgp_public_key)

        # sanity check
        if fingerprint != mailbox.pgp_finger_print:
            LOG.e("fingerprint %s different for mailbox %s", fingerprint, mailbox)
            mailbox.pgp_finger_print = fingerprint
    Session.commit()

    for contact in Contact.filter(Contact.pgp_public_key.isnot(None)).all():
        LOG.d("Load PGP key for %s", contact)
        fingerprint = load_public_key(contact.pgp_public_key)

        # sanity check
        if fingerprint != contact.pgp_finger_print:
            LOG.e("fingerprint %s different for contact %s", fingerprint, contact)
            contact.pgp_finger_print = fingerprint

    Session.commit()

    LOG.d("Finish load_pgp_public_keys")


def add_sl_domains():
    for alias_domain in ALIAS_DOMAINS:
        if SLDomain.get_by(domain=alias_domain):
            LOG.d("%s is already a SL domain", alias_domain)
        else:
            LOG.i("Add %s to SL domain", alias_domain)
            SLDomain.create(domain=alias_domain, use_as_reverse_alias=True)

    for premium_domain in PREMIUM_ALIAS_DOMAINS:
        if SLDomain.get_by(domain=premium_domain):
            LOG.d("%s is already a SL domain", premium_domain)
        else:
            LOG.i("Add %s to SL domain", premium_domain)
            SLDomain.create(
                domain=premium_domain, premium_only=True, use_as_reverse_alias=True
            )

    Session.commit()


def add_partner(partner: dict) -> Partner:
    partnerCurr = Partner.get_by(name=partner["name"])
    if not partnerCurr:
        Partner.create(
            name=partner["name"],
            contact_email=partner["contact_email"],
        )
        Session.commit()
    return partner


def set_partners():
    DEFAULT_PARTNERS = [
        {
            "is_enabled": PROTON_CLIENT_ID,
            "name": "proton",
            "contact_email": "proton@yuanyou.de",
        },
        {
            "is_enabled": GITHUB_CLIENT_ID,
            "name": "github",
            "contact_email": "github@yuanyou.de",
        },
        {
            "is_enabled": GOOGLE_CLIENT_ID,
            "name": "google",
            "contact_email": "google@yuanyou.de",
        },
        {
            "is_enabled": LINUXDO_CLIENT_ID,
            "name": "linuxdo",
            "contact_email": "linuxdo@yuanyou.de",
        },
    ]
    for partner in DEFAULT_PARTNERS:
        if partner["is_enabled"]:
            add_partner(partner)


def add_proton_partner() -> Partner:
    proton_partner = Partner.get_by(name=PROTON_PARTNER_NAME)
    if not proton_partner:
        proton_partner = Partner.create(
            name=PROTON_PARTNER_NAME,
            contact_email="paroton@yuanyou.de",
        )
        Session.commit()
    return proton_partner


if __name__ == "__main__":
    # wrap in an app context to benefit from app setup like database cleanup, sentry integration, etc
    with create_light_app().app_context():
        load_pgp_public_keys()
        add_sl_domains()
        set_partners()
