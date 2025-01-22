from requests import Session

from test_management_sync.zephyr.actions.search import find
from test_management_sync.zephyr.model.testcases import TestCaseInTree, TestCaseTreeNode, DeleteAllRequest


def new_test_case(session: Session, test_case: TestCaseInTree) -> TestCaseInTree:
    r = session.post(
        '/flex/services/rest/v3/testcase/',
        json=test_case.to_dict(),
    )
    r.raise_for_status()
    return TestCaseInTree.from_dict(r.json())


def new_test_cases(session: Session, test_cases: list[TestCaseInTree]) -> list[TestCaseInTree]:
    r = session.post(
        'flex/services/rest/v3/testcase/bulk',
        json=TestCaseInTree.schema().dump(test_cases, many=True),
    )
    r.raise_for_status()
    return TestCaseInTree.schema().load(r.json(), many=True)


def get_test_cases_for_node(session: Session, node: TestCaseTreeNode) -> list[TestCaseInTree]:
    return find(
        session=session,
        uri=f'/flex/services/rest/v3/testcase/tree/{node.id}',
        extra_params={
            'dbsearch': True,
            'order': 'orderId',
            'isascorder': True,
        },
        mapper=TestCaseInTree.from_dict,
    )


def delete_all_for_tree(session: Session, node: TestCaseTreeNode):
    r = session.delete(
        '/flex/services/rest/v3/testcase',
        params={
            'tcrCatalogTreeId': node.id,
        },
        json=DeleteAllRequest(
            ids=[],
            selected_all=0,
        ).to_dict()
    )
    r.raise_for_status()
