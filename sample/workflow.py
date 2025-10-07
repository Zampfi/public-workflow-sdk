from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

# Import activity, passing it through the sandbox without reloading the module
with workflow.unsafe.imports_passed_through():
    from sample.activity import final_activity, generate_joke, human_approval
    from sample.params import (FinalActivityInput, HumanApprovalActivityInput,
                               JokeActivityInput, WorkflowInput)


@workflow.defn
class JokeWorkflow:
    def __init__(self):
        self.state = {}

    @workflow.query(name="get_state")
    def get_state(self, query: str):
        return {"query": query, "state": self.state}

    @workflow.signal(name="change_state")
    async def change_state(self, input: str) -> None:
        # can mutate state, but does not return value
        self.state["current_state"] = input

    @workflow.run
    async def run(self, params: WorkflowInput) -> str:
        print("Starting Workflow", params.workflow_name)

        joke = await workflow.execute_activity(
            generate_joke,
            JokeActivityInput(context=params.context),
            start_to_close_timeout=timedelta(seconds=5),
        )

        human_approved = await workflow.execute_activity(
            human_approval,
            HumanApprovalActivityInput(joke=joke.joke),
            start_to_close_timeout=timedelta(seconds=5),
        )

        final_output = await workflow.execute_activity(
            final_activity,
            FinalActivityInput(
                joke=joke.joke, human_approved=human_approved.human_approved
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

        return final_output


@workflow.defn
class TestWorkflow:
    def __init__(self):
        self.state = {}

    @workflow.query
    def query_handler(self, query: str):
        return {"query": query, "state": self.state}

    @workflow.run
    async def run(self, params: WorkflowInput) -> str:
        print("Starting Workflow", params.workflow_name)

        joke = await workflow.execute_activity(
            generate_joke,
            JokeActivityInput(context=params.context),
            start_to_close_timeout=timedelta(seconds=5),
        )

        human_approved = await workflow.execute_activity(
            human_approval,
            HumanApprovalActivityInput(joke=joke.joke),
            start_to_close_timeout=timedelta(seconds=5),
        )

        final_output = await workflow.execute_activity(
            final_activity,
            FinalActivityInput(
                joke=joke.joke, human_approved=human_approved.human_approved
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        return final_output
