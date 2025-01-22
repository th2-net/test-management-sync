from requests import Session

from test_management_sync.zephyr.actions.search import find
from test_management_sync.zephyr.model.testcases import TestCaseTreeNode
from test_management_sync.zephyr.model.planning import Cycle, Phase, Execution, AssignmentTree, \
    TestCasesAssignment, ExecutionsStatusUpdate


def create_cycle(session: Session, cycle: Cycle) -> Cycle:
    r = session.post(
        '/flex/services/rest/v3/cycle',
        json=cycle.to_dict(),
    )
    r.raise_for_status()
    return Cycle.from_dict(r.json())


def delete_cycle(session: Session, cycle: Cycle):
    r = session.delete(
        f'/flex/services/rest/v3/cycle/{cycle.id}',
    )
    r.raise_for_status()


def get_cycles_for_release(session: Session, release_id: int) -> list[Cycle]:
    r = session.get(
        f'/flex/services/rest/v3/cycle/release/{release_id}',
    )
    r.raise_for_status()
    return Cycle.schema().load(r.json(), many=True)


def create_cycle_phase_from_test_case_tree(
        session: Session,
        cycle: Cycle,
        tree_node: TestCaseTreeNode,
) -> Phase:
    r = session.post(
        f'/flex/services/rest/v3/cycle/{cycle.id}/phase',
        json=Phase(
            phase_start_date=cycle.cycle_start_date,
            phase_end_date=cycle.cycle_end_date,
            cycle_id=cycle.id,
            release_id=cycle.release_id,
            name=tree_node.name,
            tcr_catalog_tree_id=tree_node.id,
            free_form=False,
        ).to_dict()
    )
    r.raise_for_status()
    return Phase.from_dict(r.json())


def create_cycle_phase_free_form(
        session: Session,
        cycle: Cycle,
        name: str,
) -> Phase:
    r = session.post(
        f'/flex/services/rest/v3/cycle/{cycle.id}/phase',
        json=Phase(
            phase_start_date=cycle.cycle_start_date,
            phase_end_date=cycle.cycle_end_date,
            cycle_id=cycle.id,
            release_id=cycle.release_id,
            name=name,
            free_form=True,
        ).to_dict()
    )
    r.raise_for_status()
    return Phase.from_dict(r.json())


def assign_executions_to_creators(session: Session, phase: Phase):
    r = session.post(
        f'/flex/services/rest/v3/assignmenttree/{phase.id}/assign'
    )
    r.raise_for_status()


def assign_all_unassigned_to_user(session: Session, phase: Phase, assignment_node: AssignmentTree, user_id: int):
    r = session.put(
        f'/flex/services/rest/v3/assignmenttree/{phase.id}/bulk/tree/{assignment_node.id}/from/-1/to/{user_id}',
        params={
            'cascade': True,
            'easmode': 2,
        }
    )
    r.raise_for_status()


def get_executions_for_cycle_phase(session: Session, release_id: int, phase: Phase) -> list[Execution]:
    return find(
        session=session,
        uri='/flex/services/rest/v3/execution',
        extra_params={
            'releaseid': release_id,
            'cyclephaseid': phase.id,
            'dbsearch': True,
            'isascorder': True,
            'order': 'orderId',
        },
        mapper=Execution.from_dict,
    )


def get_assignment_tree(session: Session, phase: Phase) -> AssignmentTree:
    r = session.get(
        f'/flex/services/rest/v3/assignmenttree/{phase.id}'
    )
    r.raise_for_status()
    return AssignmentTree.from_dict(r.json())


def assign_test_cases_to_phase(session: Session, phase: Phase,
                               assignments: list[TestCasesAssignment], include_hierarchy: bool = True):
    r = session.post(
        f'/flex/services/rest/v3/assignmenttree/{phase.id}/assign/bytree/{phase.tcr_catalog_tree_id}',
        params={'includehierarchy': include_hierarchy},
        json=TestCasesAssignment.schema().dump(assignments, many=True),
    )
    r.raise_for_status()


def assign_test_case_to_phase_node(session: Session, phase: Phase, assignment_node: AssignmentTree,
                                   assignments: list[TestCasesAssignment], include_hierarchy: bool = True):
    r = session.post(
        f'/flex/services/rest/v3/assignmenttree/{phase.id}/assign/bytree/{assignment_node.id}',
        params={'includehierarchy': include_hierarchy},
        json=TestCasesAssignment.schema().dump(assignments, many=True),
    )
    r.raise_for_status()


def execute_test_cases(session: Session, status: str, tester_id: int, execution_ids: list[int]):
    r = session.put(
        '/flex/services/rest/v3/execution/bulk',
        params={
            'status': status,
            'testerid': tester_id,
            'allExecutions': True,
        },
        json=ExecutionsStatusUpdate(
            ids=execution_ids,
            teststep_update=False,
            teststep_status_id=1,
        ).to_dict()
    )
    r.raise_for_status()
