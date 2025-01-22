from requests import Session

from test_management_sync.zephyr.model.user import UserInfo


def get_user_id(session: Session) -> int:
    res = session.get('/flex/services/rest/latest/user/current')
    res.raise_for_status()
    user_info = UserInfo.from_dict(res.json())
    return user_info.id
