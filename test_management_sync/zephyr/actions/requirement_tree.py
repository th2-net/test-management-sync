from requests import Session

from test_management_sync.zephyr.model.requirements import RequirementTreeNode


def new_requirement_tree_node(session: Session, node: RequirementTreeNode) -> RequirementTreeNode:
    r = session.post(
        '/flex/services/rest/v3/requirementtree/add',
        json=node.to_dict(),
    )
    r.raise_for_status()
    return RequirementTreeNode.from_dict(r.json())


def get_requirement_tree_root_nodes(session: Session, project_id: int,
                                    release_id: int = None) -> list[RequirementTreeNode]:
    query_params = {'projectId': project_id}
    if release_id is not None:
        query_params['releaseid'] = release_id
    r = session.get(
        '/flex/services/rest/v4/requirementtree',
        params=query_params,
    )
    r.raise_for_status()
    return RequirementTreeNode.schema().load(r.json(), many=True)


def get_requirement_tree_node_details(session: Session, requirement_tree_node_id: int) -> RequirementTreeNode:
    r = session.get(
        f'/flex/services/rest/v4/requirementtree/{requirement_tree_node_id}'
    )
    r.raise_for_status()
    return RequirementTreeNode.from_dict(r.json())


def remove_requirement_tree_node(session: Session, node: RequirementTreeNode):
    r = session.delete(
        f'/flex/services/rest/v3/requirementtree/sync/{node.id}',
        params={
            'releaseid': node.release_id,
        },
    )
    r.raise_for_status()
