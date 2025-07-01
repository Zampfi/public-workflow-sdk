from dataclasses import dataclass, field
from typing import Sequence

from temporalio.client import Client
from temporalio.service import TLSConfig

from zamp_public_workflow_sdk.temporal.data_converters.base import BaseDataConverter
from zamp_public_workflow_sdk.temporal.models.temporal_models import (
    CancelWorkflowParams, CancelWorkflowResponse, GetWorkflowDetailsParams,
    ListWorkflowParams, QueryWorkflowParams, QueryWorkflowResponse,
    RunWorkflowParams, RunWorkflowResponse, SignalWorkflowParams,
    SignalWorkflowResponse, TerminateWorkflowParams, TerminateWorkflowResponse,
    WorkflowDetailsResponse, WorkflowResponse)
from zamp_public_workflow_sdk.temporal.temporal_client import TemporalClient
from zamp_public_workflow_sdk.temporal.temporal_worker import (TemporalWorker,
                                                       TemporalWorkerConfig)

from typing import Sequence
from dataclasses import field
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig


async def init_runtime_with_prometheus(address: str) -> Runtime:
    # Create runtime for use with Prometheus metrics
    return Runtime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(bind_address=address)
        )
    )

@dataclass
class TemporalClientConfig:
    host: str = "localhost:7233"
    namespace: str = "default"
    client_cert: str | None = ""
    client_key: str | None = ""
    server_root_ca_cert: str | None = ""
    is_cloud: bool = False
    data_converter: BaseDataConverter = BaseDataConverter()
    interceptors: Sequence[object] = field(default_factory=list)
    prometheus_address: str | None = ""

class TemporalService:
    def __init__(self, client: TemporalClient):
        self.workflow_manager = client

    @staticmethod
    async def connect(
        config: TemporalClientConfig
    ):
        """Build Temporal client and create service instance"""

        if not config.is_cloud:
            client = await Client.connect(
                config.host,
                namespace=config.namespace,
                data_converter=config.data_converter.get_converter(),
                interceptors=config.interceptors
            )
        else:
            if not all([config.client_cert, config.client_key]):
                raise ValueError("client_cert and client_key are required for cloud connection")

            tls_config = TLSConfig(
                client_cert=config.client_cert.encode('utf-8'),
                client_private_key=config.client_key.encode('utf-8'),
                server_root_ca_cert=config.server_root_ca_cert.encode('utf-8') if config.server_root_ca_cert else None,
            )

            # Create runtime with prometheus if address is provided
            runtime = None
            if config.prometheus_address:
                runtime = await init_runtime_with_prometheus(config.prometheus_address)

            client = await Client.connect(
                config.host,
                namespace=config.namespace,
                tls=tls_config,
                data_converter=config.data_converter.get_converter(),
                interceptors=config.interceptors,
                runtime=runtime
            )

        temporal_client = TemporalClient(client)

        return TemporalService(temporal_client)

    async def worker(self, config: TemporalWorkerConfig):
        return TemporalWorker(self.workflow_manager, config)

    async def start_async_workflow(self, params: RunWorkflowParams) -> RunWorkflowResponse:
        return await self.workflow_manager.start_async_workflow(params)

    async def start_sync_workflow(self, params: RunWorkflowParams) -> RunWorkflowResponse:
        return await self.workflow_manager.start_sync_workflow(params)

    async def list_workflows(self, params: ListWorkflowParams) -> list[WorkflowResponse]:
        return await self.workflow_manager.list_workflows(params)

    async def get_workflow_details(self, params: GetWorkflowDetailsParams) -> WorkflowDetailsResponse:
        return await self.workflow_manager.get_workflow_details(params)

    async def query_workflow(self, params: QueryWorkflowParams) -> QueryWorkflowResponse:
        return await self.workflow_manager.query_workflow(params)

    async def signal_workflow(self, params: SignalWorkflowParams) -> SignalWorkflowResponse:
        return await self.workflow_manager.signal_workflow(params)

    async def cancel_workflow(self, params: CancelWorkflowParams) -> CancelWorkflowResponse:
        return await self.workflow_manager.cancel_workflow(params)

    async def terminate_workflow(self, params: TerminateWorkflowParams) -> TerminateWorkflowResponse:
        return await self.workflow_manager.terminate_workflow(params)