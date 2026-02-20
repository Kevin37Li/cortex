"""Shared helpers for LangGraph workflow nodes."""

import functools
import logging
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, TypeVar, cast

logger = logging.getLogger(__name__)

NodeFuncT = TypeVar(
    "NodeFuncT",
    bound=Callable[[Any], Awaitable[Any]],
)


def _build_log_context(state: Mapping[str, Any]) -> dict[str, Any]:
    """Extract context fields commonly used across workflow logs."""
    context: dict[str, Any] = {}

    item_id = state.get("item_id")
    if item_id is not None:
        context["item_id"] = item_id

    query = state.get("query")
    if query is not None:
        context["query"] = query

    return context


def log_node_execution(node_name: str) -> Callable[[NodeFuncT], NodeFuncT]:
    """Decorator for logging node entry/exit with consistent metadata."""

    def decorator(func: NodeFuncT) -> NodeFuncT:
        @functools.wraps(func)
        async def wrapper(state: Any) -> Any:
            state_mapping: Mapping[str, Any]
            if isinstance(state, Mapping):
                state_mapping = state
            else:
                logger.warning(
                    "log_node_execution: state is not a Mapping (type=%s), skipping context",
                    type(state).__name__,
                )
                state_mapping = {}

            context = _build_log_context(state_mapping)

            logger.info(f"Starting node: {node_name}", extra=context)
            try:
                result = await func(state)
                logger.info(f"Completed node: {node_name}", extra=context)
                return result
            except Exception as e:
                logger.error(
                    f"Failed node: {node_name}",
                    extra={**context, "error": str(e)},
                )
                raise

        return cast(NodeFuncT, wrapper)

    return decorator


def route_or_error(next_node: str) -> Callable[[Mapping[str, Any]], str]:
    """Route to the next node unless an error is present in state."""

    def router(state: Mapping[str, Any]) -> str:
        if state.get("error"):
            return "handle_error"
        return next_node

    return router
