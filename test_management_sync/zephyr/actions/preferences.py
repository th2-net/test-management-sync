from requests import Session

from test_management_sync.zephyr.model.preferences import Preference


def get_system_preferences(session: Session) -> list[Preference]:
    r = session.get(
        '/flex/services/rest/v4/admin/preference/all/system',
    )
    r.raise_for_status()
    return Preference.schema().load(r.json(), many=True)
