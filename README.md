# test management sync

This is the library to synchronize test execution with different test management platforms.

Supported platforms:
+ Zephyr Enterprise (7.17.1)

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

```console
pip install test-management-sync
```

## Usage

The library usages `Manager` as an object to perform the synchronization with test management platform.
The manager is generic and does not depend on a particula test management platform.
The bridge between `Manager` and platform implementation is a `Service`.
`Manager` accepts the instance of a `Service` and uses it to interact with test management platform.

```python
from test_management_sync import *

with Manager(service=...) as manager:
    # main logic
    pass
```

### Common model

The `Manager` operates with common model. It consists of:
+ Folder/RootFolder
+ Requirement
+ TestCase
+ Cycle
+ Phase
+ ExecutionStatus

#### Folder/RootFolder

Those objects define hierarchy of elements in the test management platform.
They can be used with `TestCase`s and `Requirement`s.

#### Requirement

`Requirement` object corresponds to the system requirement.
The `Requirement` matches to the test management platform's requirement only by `name` and `description`.
The location of the `Requirement` is defined by `folder` attribute.
If any of those attributes changed the `Requirement` will be treated as a new one.

#### TestCase

`TestCase` object corresponds to a test case in test management platform.
The `TestCase` matches to the test case in test management platform only by `name` and `description`.
The location of the `TestCase` is defined by `folder` attribute.
If any of those attributes changed the `TestCase` will be treated as a new one.

#### Cycle

`Cycle` object corresponds to the test cycle in test management platform.
The `Cycle` matches to the test cycle in test management platform requirement only by `name` and its `start` and `end` dates.
If any of those attributes changed the `Cycle` will be treated as a new one.

#### Phase

`Phase` is a part of `Cycle`. It is defined by its name. If the name changes the phase will be considered as a new one.

#### ExecutionStatus

`ExecutionStatus` is statuses available in the system that can be set for test case execution.

### Update test management platform state

Here you can find a sample code with comments that shows what you can do with the `Manager`.

```python
from pathlib import Path
from datetime import date
from test_management_sync import *

with Manager(service=...) as manager:
    # Requirements:
    #
    # Functional
    # |- NewOrderSingle
    # |  |- New tag 42
    # |- Support MarketDataRequest
    # NonFunctional
    # |- Survive 10k/s load

    # root folder for functional requirements
    functional_req = RootFolder('Functional')
    # sub folder
    functional_req_nos = functional_req / 'NewOrderSingle'
    nos_new_tag_42 = Requirement(name='New tag 42', description='new tag added to NOS message',
                                 folder=functional_req_nos)
    mdr_new_type = Requirement(name='Support MarketDataRequest', description='support for new message type MD req',
                               folder=functional_req)
    # root folder for non-functional requirements
    non_functional_req = RootFolder('NonFunctional')
    load_req = Requirement(name='Survive 10k/s load', description='system should be alive under 10000 msg/s',
                           folder=non_functional_req)

    # create requirements
    # if force=True all requirement trees in specified requirements will be cleaned before creating new requirements
    # if requirement already exists it won't be created
    manager.create_requirements(requirements=[nos_new_tag_42, mdr_new_type, load_req], force=False)

    # Testcases:
    # Functional
    # |- NewOrderSingle
    # |  |- Send NewOrderSingle with tag 42
    # |  |- Send NewOrderSingle with market type
    # |- Send MarketDataRequest
    # NonFunctional
    # |- Load the system with 10k/s for 5 minutes
    functional_tcs = RootFolder('Functional')
    functional_tcs_nos = functional_tcs / 'NewOrderSingle'
    send_nos_42 = TestCase(name='Send NewOrderSingle with tag 42', description='send NOS with new tag 42',
                           folder=functional_tcs_nos)
    send_nos_market = TestCase(name='Send NewOrderSingle with market type', description='send NOS with market type',
                               folder=functional_tcs_nos)
    md_send = TestCase(name='Send MarketDataRequest', description='send new MD message', folder=functional_tcs)
    non_functional_tc = RootFolder('NonFunctional')
    load = TestCase(name='Load the system with 10k/s for 5 minutes', description='send 10000 mgs/s to the system',
                    folder=non_functional_tc)

    # create testcases
    # if force=True all testcase trees in specified testcases will be cleaned before creating new testcases
    # if testcase already exists it won't be created
    manager.create_test_cases(test_cases=[send_nos_42, send_nos_market, md_send, load], force=False)

    # map testcases to requirements
    manager.map_test_cases_to_requirements(
        {
            nos_new_tag_42: [send_nos_42],
            mdr_new_type: [md_send],
            load_req: [load],
        }
    )

    # test cycle to attach testcases
    cycle = Cycle(name='Test cycle', start_date=date.today(), end_date=date.today())
    # creates test cycle
    # if force=True the existing cycle will be removed
    # if cycle already exists no new cycle will be created
    manager.create_cycle(cycle, force=False)
    # creates phase from the root folder
    # all testcases in that hierarchy will be added to the phase
    manager.create_phase_from_testcase_tree(cycle=cycle, phase_root=non_functional_tc)
    # creates a free-form phase from specified testcase
    # folder hierarchy is preserved
    manager.create_phase_from_testcases(cycle=cycle, phase_name='FunctionalA', test_cases=[send_nos_42, md_send])
    # you can use any of those two methods depending on what you need

    # status with display name 'Pass'
    passed_status = manager.execution_status_for_name('Pass')

    # status with display name 'Fail'
    failed_status = manager.execution_status_for_name('Fail')

    # set specified status for test case executions in provided cycle
    manager.execute_testcases(cycle=cycle, status=passed_status, test_cases=[send_nos_42, load])
    manager.execute_testcases(cycle=cycle, status=failed_status, test_cases=[md_send])

    # you can attach files to requirements
    manager.attach_files_to_requirements(
        {
            nos_new_tag_42: [Path('spec.pdf')]
        },
        # will replace file with same name if already attached to the element
        # otherwise, will attach a new file and keep the old one
        replace_existing=True,
    )

    # and to test cases
    manager.attach_files_to_testcases(
        {
            load: [Path('performance.script')]
        },
        replace_existing=True,
    )

    # and to test case execution
    manager.attach_files_to_executions(
        cycle=cycle,
        attachments={
            load: [Path('availability_graph_2024_02_27.txt')]
        },
        replace_existing=False,
    )

    last_statuses_by_tc = manager.get_last_execution_status_for_testcases(
        cycle=cycle,
        test_cases=[send_nos_42, load, md_send],
    )
```

### Zephyr Enterprise

`ZephyrService` can be used to work with ZephyrEnterprise 7.17.1 (other versions might not work)

```python
from test_management_sync import *
from test_management_sync.zephyr import ZephyrService

with Manager(
    service=ZephyrService(
        zephyr_url='https://zephyr.com',
        api_token='<API TOKEN>', # can be retrieved from zephyr UI
        project_id=42, # can be found in zephyr UI
        release_id=54, # can be found in zephyr UI
    )
) as manager:
    # logic
    pass
```

## License

`test-management-sync` is distributed under the terms of the [Apache License 2.0](https://spdx.org/licenses/Apache-2.0.html) license.
