from .types import OpenAIPayload


# TODO: BaseProvider.optimize_payload() 훅을 통해 연결 필요
def prune_reasoning_items(payload: OpenAIPayload) -> OpenAIPayload:
    raise NotImplementedError
