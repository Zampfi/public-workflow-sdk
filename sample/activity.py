from __future__ import annotations

from temporalio import activity

from sample.params import (FinalActivityInput, FinalActivityOutput,
                           HumanApprovalActivityInput,
                           HumanApprovalActivityOutput, JokeActivityInput,
                           JokeActivityOutput, YourParams)


@activity.defn
async def say_hello(params: YourParams) -> str:
    return f"Hello, {params.name}!"


@activity.defn
async def generate_joke(params: JokeActivityInput) -> JokeActivityOutput:
    return JokeActivityOutput(
        context=params.context, joke="Why did the chicken cross the road?"
    )


# human in the loop
@activity.defn
async def human_approval(
    params: HumanApprovalActivityInput,
) -> HumanApprovalActivityOutput:
    return HumanApprovalActivityOutput(joke=params.joke, human_approved=True)


@activity.defn
async def final_activity(params: FinalActivityInput) -> FinalActivityOutput:
    return FinalActivityOutput(joke=params.joke, human_approved=params.human_approved)
