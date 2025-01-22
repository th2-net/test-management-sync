from requests import Session

from test_management_sync.zephyr.model.testcases import TestCaseTreeNode


def create_test_case_tree_node(session: Session, node: TestCaseTreeNode,
                               parent: TestCaseTreeNode = None) -> TestCaseTreeNode:
    parent_id = 0 if parent is None else parent.id
    if parent is not None:
        node.type = 'Module'
    r = session.post(
        '/flex/services/rest/v3/testcasetree',
        params={'parentid': parent_id},
        json=node.to_dict(),
    )
    r.raise_for_status()
    return TestCaseTreeNode.from_dict(r.json())


def get_test_case_tree_root_nodes(session: Session, release_id: int) -> list[TestCaseTreeNode]:
    return _get_test_case_tree_node(session, release_id, 'Phase')


def get_test_case_tree_sub_nodes(session: Session, release_id: int, parent: TestCaseTreeNode) -> list[TestCaseTreeNode]:
    return _get_test_case_tree_node(session, release_id, 'Module', parent.id)


def _get_test_case_tree_node(session: Session, release_id: int, note_type: str, parent_id: int = None):
    params = {
        'type': note_type,
        'releaseid': release_id
    }
    if parent_id is not None:
        params['parentid'] = parent_id
    r = session.get(
        '/flex/services/rest/v3/testcasetree/lite',
        params=params
    )
    r.raise_for_status()
    return TestCaseTreeNode.schema().load(r.json(), many=True)
