from requests import Session

from test_management_sync.zephyr.actions.search import find
from test_management_sync.zephyr.model.requirements import Requirement, RequirementTreeNode, \
    BulkRequirementTestCasesMapping, TreePath, DeleteAllRequest
from test_management_sync.zephyr.model.testcases import TestCaseInTree, TestCaseTreeNode


def new_requirement(session: Session, requirement: Requirement) -> Requirement:
    r = session.post(
        '/flex/services/rest/v3/requirement/',
        json=requirement.to_dict(),
    )
    r.raise_for_status()
    return Requirement.from_dict(r.json())


def find_requirements(session: Session, release_id: int, node: RequirementTreeNode) -> list[Requirement]:
    return find(
        session,
        uri='/flex/services/rest/v3/requirement',
        extra_params={
            'requirementtreeid': node.id,
            'releaseid': release_id,
        },
        mapper=Requirement.from_dict,
    )


def delete_all_for_tree(session: Session, release_id: int, node: RequirementTreeNode):
    r = session.delete(
        '/flex/services/rest/v3/requirement/sync',
        params={
            'releaseid': release_id,
            'requirementTreeId': node.id,
        },
        json=DeleteAllRequest(
            ids=[],
            selected_all=0,
        ).to_dict()
    )
    r.raise_for_status()


def map_requirement_to_test_cases(
        session: Session,
        release_id: int,
        requirement: Requirement,
        test_cases: list[TestCaseInTree],
        test_cases_tree_nodes: list[TestCaseTreeNode],
):
    req_payload = BulkRequirementTestCasesMapping(
        mod_tcr_catalog_tree=list(map(__to_tc_tree_path, test_cases_tree_nodes)),
        requirement_id=requirement.id,
        mod_testcase=list(map(__to_tc_tree, test_cases)),
        release_id=release_id,
    )

    r = session.put(
        '/flex/services/rest/v3/requirement/allocate/testcase',
        json=req_payload.to_dict(),
    )
    r.raise_for_status()


def __to_tc_tree_path(tc_tree_node: TestCaseTreeNode) -> TreePath:
    return [tc_tree_node.id, 0]


def __to_tc_tree(tc_in_tree: TestCaseInTree) -> TreePath:
    return [tc_in_tree.tcr_catalog_tree_id, tc_in_tree.testcase.testcase_id]
