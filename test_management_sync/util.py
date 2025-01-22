from collections import defaultdict

from test_management_sync.model import TestCase, Folder, Requirement


def group_tc_by_folder(test_cases: list[TestCase]) -> dict[Folder, list[TestCase]]:
    tcs_by_folder = defaultdict[Folder, list[TestCase]](list)
    for tc in test_cases:
        tcs_by_folder[tc.folder].append(tc)
    return tcs_by_folder


def group_req_by_folder(requirements: list[Requirement]) -> dict[Folder, list[Requirement]]:
    req_by_folder = defaultdict[Folder, list[Requirement]](list)
    for req in requirements:
        req_by_folder[req.folder].append(req)
    return req_by_folder
