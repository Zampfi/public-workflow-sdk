from dataclasses import dataclass


# ...
# ...
@dataclass
class YourParams:
    name: str

# a decorator called @input_param , @output_param : where we add validations and other stuff
@dataclass
class WorkflowInput:
    workflow_name: str
    tenant_id: str
    context: str

@dataclass
class WorkflowOutput:
    joke: str
    human_approved: bool


# activities
@dataclass
class JokeActivityInput:
    context: str

@dataclass
class JokeActivityOutput:
    context: str
    joke: str

@dataclass
class HumanApprovalActivityInput:
    joke: str

@dataclass
class HumanApprovalActivityOutput:
    joke: str
    human_approved: bool

@dataclass
class FinalActivityInput:
    joke: str
    human_approved: bool

@dataclass
class FinalActivityOutput:
    joke: str
    human_approved: bool
