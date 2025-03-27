class SLException(Exception):
    def __str__(self):
        super_str = super().__str__()
        return f"{type(self).__name__} {super_str}"

    def error_for_user(self) -> str:
        """By default send the exception errror to the user. Should be overloaded by the child exceptions"""
        return str(self)


class AliasInTrashError(SLException):
    """别名已被删除，抛出异常"""

    pass


class DirectoryInTrashError(SLException):
    """目录已被删除，抛出异常"""

    pass


class SubdomainInTrashError(SLException):
    """子域名已被删除，抛出异常"""

    pass


class CannotCreateContactForReverseAlias(SLException):
    """raised when a contact is created that has website_email=reverse_alias of another contact"""

    def error_for_user(self) -> str:
        return "你不能将一个反向别名创建为联系人，抛出异常"


class NonReverseAliasInReplyPhase(SLException):
    """在回复阶段使用非反向别名时引发"""

    pass


class VERPTransactional(SLException):
    """raised an email sent to a transactional VERP can't be handled"""

    pass


class VERPForward(SLException):
    """raised an email sent to a forward VERP can't be handled"""

    pass


class VERPReply(SLException):
    """raised an email sent to a reply VERP can't be handled"""

    pass


class MailSentFromReverseAlias(SLException):
    """raised when receiving an email sent from a reverse alias"""

    pass


class ProtonPartnerNotSetUp(SLException):
    pass


class PartnerNotSetUp(SLException):
    pass


class ErrContactErrorUpgradeNeeded(SLException):
    """raised when user cannot create a contact because the plan doesn't allow it"""

    def error_for_user(self) -> str:
        return "Please upgrade to premium to create reverse-alias"


class ErrAddressInvalid(SLException):
    """raised when an address is invalid"""

    def __init__(self, address: str):
        self.address = address

    def error_for_user(self) -> str:
        return f"{self.address} is not a valid email address"


class InvalidContactEmailError(SLException):
    def __init__(self, website_email: str):  # noqa: F821
        self.website_email = website_email

    def error_for_user(self) -> str:
        return f"Cannot create contact with invalid email {self.website_email}"


class ErrContactAlreadyExists(SLException):
    """raised when a contact already exists"""

    # TODO: type-hint this as a contact when models are almost dataclasses and don't import errors
    def __init__(self, contact: "Contact"):  # noqa: F821
        self.contact = contact

    def error_for_user(self) -> str:
        return f"{self.contact.website_email} is already added"


class LinkException(SLException):
    def __init__(self, message: str):
        self.message = message


class AccountAlreadyLinkedToAnotherPartnerException(LinkException):
    def __init__(self):
        super().__init__("This account is already linked to another partner")


class AccountAlreadyLinkedToAnotherUserException(LinkException):
    def __init__(self):
        super().__init__("This account is linked to another user")


class AccountIsUsingAliasAsEmail(LinkException):
    def __init__(self):
        super().__init__("Your account has an alias as it's email address")


class ProtonAccountNotVerified(LinkException):
    def __init__(self):
        super().__init__(
            "The Proton account you are trying to use has not been verified"
        )


class PartnerAccountNotVerified(LinkException):
    def __init__(self):
        super().__init__("您尝试使用的帐户尚未经过验证")
