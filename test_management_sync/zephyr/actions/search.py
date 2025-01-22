from typing import TypeVar, Callable

from requests import Session

from test_management_sync.zephyr.model.search import SearchResult

T = TypeVar("T")


def find(session: Session, uri: str, extra_params: dict, mapper: Callable[[dict], T]) -> list[T]:
    result = []
    offset = 0
    next_request = True
    page_size = 100

    while next_request:
        search_params = {
            'offset': offset,
            'pagesize': page_size,
        }
        search_params.update(extra_params)
        r = session.get(uri, params=search_params)
        r.raise_for_status()

        search_result = SearchResult.schema().from_dict(r.json())
        search_result_objects = search_result.results
        next_request = len(search_result_objects) == page_size
        for r in search_result_objects:
            result.append(mapper(r))
        offset += page_size

    return result

