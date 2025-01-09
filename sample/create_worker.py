import asyncio

from sample.activity import final_activity, generate_joke, human_approval
from sample.workflow import JokeWorkflow
from zamp_public_workflow_sdk.temporal.temporal_service import (TemporalClientConfig,
                                                        TemporalService)
from zamp_public_workflow_sdk.temporal.temporal_worker import (Activity,
                                                       TemporalWorkerConfig,
                                                       Workflow)


async def main():
    service = await TemporalService.connect(
        TemporalClientConfig(
            host="localhost:7233",
            namespace="default",
            is_cloud=False
        )
    )
    activities = [Activity(name="generate_joke", func=generate_joke), Activity(name="human_approval", func=human_approval), Activity(name="final_activity", func=final_activity)]
    workflows = [Workflow(name="JokeWorkflow", workflow=JokeWorkflow)]

    worker = await service.worker(TemporalWorkerConfig(
        task_queue="joke-queue",
        activities=activities,
        workflows=workflows
    ))
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
