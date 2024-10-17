from ..base import BaseNode
from .llm import (
    AdvancedLLMNode,
    AdvancedLLMNodeInput,
    AdvancedLLMNodeOutput,
    AdvancedLLMNodeConfig,
)
from typing import List, Dict
from difflib import SequenceMatcher
import asyncio


class SelfConsistencyNodeConfig(AdvancedLLMNodeConfig):
    samples: int = 5
    similarity_threshold: float = 0.8


class SelfConsistencyNodeInput(AdvancedLLMNodeInput):
    pass


class SelfConsistencyNodeOutput(AdvancedLLMNodeOutput):
    pass


class SelfConsistencyNode(
    BaseNode[
        SelfConsistencyNodeConfig, SelfConsistencyNodeInput, SelfConsistencyNodeOutput
    ]
):
    name = "self_consistency_node"

    def __init__(self, config: SelfConsistencyNodeConfig) -> None:
        self.config = config

        # Initialize the LLM node for generating samples
        llm_node_config = AdvancedLLMNodeConfig.model_validate(config.model_dump())
        self._llm_node = AdvancedLLMNode(llm_node_config)

        # Set input and output types
        self.InputType = self._llm_node.InputType
        self.OutputType = SelfConsistencyNodeOutput  # Ensure OutputType is set to SelfConsistencyNodeOutput

    async def _generate_responses(
        self, input_data: AdvancedLLMNodeInput
    ) -> List[AdvancedLLMNodeOutput]:
        tasks = [self._llm_node(input_data) for _ in range(self.config.samples)]
        return await asyncio.gather(*tasks)

    def _calculate_similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    def _cluster_similar_responses(self, responses: List[str]) -> List[List[str]]:
        clusters = []
        for response in responses:
            added_to_cluster = False
            for cluster in clusters:
                if (
                    self._calculate_similarity(response, cluster[0])
                    >= self.config.similarity_threshold
                ):
                    cluster.append(response)
                    added_to_cluster = True
                    break
            if not added_to_cluster:
                clusters.append([response])
        return clusters

    async def __call__(
        self, input_data: SelfConsistencyNodeInput
    ) -> SelfConsistencyNodeOutput:
        responses = await self._generate_responses(input_data)
        response_texts = [
            response.text for response in responses
        ]  # Assuming response has a 'text' attribute
        clusters = self._cluster_similar_responses(response_texts)

        # Sort clusters by frequency and select the most frequent one
        clusters.sort(key=lambda x: len(x), reverse=True)
        best_cluster = clusters[0] if clusters else []

        # Return the representative answer from the best cluster
        best_response_text = (
            best_cluster[0] if best_cluster else "No consistent answer found."
        )
        return SelfConsistencyNodeOutput(
            text=best_response_text
        )  # Ensure correct instantiation of SelfConsistencyNodeOutput