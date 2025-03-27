from abc import ABC, abstractmethod
from dataclasses import dataclass
from http import HTTPStatus
from requests import Response, Session
from typing import Optional

from app.account_linking import SLPlan, SLPlanType
from app.log import LOG


PLAN_FREE = 1
PLAN_PREMIUM = 2
PLAN_PREMIUM_LIFETIME = 3


@dataclass
class UserInformation:
    email: str
    name: str
    id: str
    plan: SLPlan


@dataclass
class PartnerUser:
    id: str
    name: str
    email: str
    plan: SLPlan


@dataclass
class AccessCredentials:
    access_token: str
    session_id: str


def convert_access_token(access_token_response: str) -> AccessCredentials:
    """
    The Access token response contains both the Proton Session ID and the Access Token.
    The Session ID is necessary in order to use the Proton API. However, the OAuth response does not allow us to return
    extra content.
    This method takes the Access token response and extracts the session ID and the access token.
    """
    parts = access_token_response.split("-")
    if len(parts) != 3:
        raise Exception("Invalid access token response")
    if parts[0] != "pt":
        raise Exception("Invalid access token response format")
    return AccessCredentials(
        session_id=parts[1],
        access_token=parts[2],
    )


class PartnerClient(ABC):
    @abstractmethod
    def get_user(self) -> Optional[UserInformation]:
        pass


class HttpPartnerClient(PartnerClient):
    def __init__(
        self,
        base_url: str,
        credentials: AccessCredentials,
        original_ip: Optional[str],
        verify: bool = True,
    ):
        self.base_url = base_url
        self.access_token = credentials
        client = Session()
        client.verify = verify
        headers = {
            "authorization": f"Bearer {credentials}",
        }

        if original_ip is not None:
            headers["x-forwarded-for"] = original_ip
        client.headers.update(headers)
        self.client = client

    def get_user(self) -> Optional[UserInformation]:
        info = self.__get()
        # LOG.debug(f"get user_info {info}")
        return UserInformation(
            email=str(info.get("email")),
            name=info.get("name"),
            id=str(info.get("id")),
            plan=SLPlan(type=SLPlanType.Free, expiration=None),
        )

    def __get(self) -> dict:
        url = f"{self.base_url}"
        res = self.client.get(url)
        return self.__validate_response(res)

    @staticmethod
    def __validate_response(res: Response) -> dict:
        status = res.status_code
        as_json = res.json()
        if status != HTTPStatus.OK:
            LOG.error("oauth获取用户信息失败")
            return False
        return as_json
