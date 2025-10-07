from __future__ import annotations

import asyncio

from sample.api import (cancel_workflow, get_workflow_details, list_workflows,
                        query_workflow, run_workflow, signal_workflow,
                        terminate_workflow)


async def main():
    # run workflow
    print(await run_workflow())
    print(await list_workflows())
    print(await get_workflow_details())
    print(await query_workflow())
    print(await signal_workflow())
    print(await cancel_workflow())
    print(await terminate_workflow())


if __name__ == "__main__":
    asyncio.run(main())
