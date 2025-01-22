from requests import Session
from urllib.parse import urljoin


class ZephyrSession(Session):
    def __init__(self, prefix_url: str, api_token: str):
        self.prefix_url = prefix_url
        super(ZephyrSession, self).__init__()
        self.headers.update(
            {
                'Authorization': f'Bearer {api_token}'
            }
        )

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        return super(ZephyrSession, self).request(method, url, *args, **kwargs)
