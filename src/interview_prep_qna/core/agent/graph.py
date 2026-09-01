import logging
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from interview_prep_qna.core.agent.answer import AnswerAgent
from interview_prep_qna.core.agent.contextualizer import ContextualizerAgent
from interview_prep_qna.core.agent.enums import GradingAction
from interview_prep_qna.core.agent.escalation.github_live import GitHubLiveAgent
from interview_prep_qna.core.agent.escalation.web_search import WebSearchAgent
from interview_prep_qna.core.agent.generic import GenericAgent
from interview_prep_qna.core.agent.grading import GradingAgent
from interview_prep_qna.core.agent.interrogator import InterrogatorAgent
from interview_prep_qna.core.agent.retrieval import RAGPipeline
from interview_prep_qna.core.agent.router import RouterAgent
from interview_prep_qna.core.agent.state import AgentState
from interview_prep_qna.core.agent.summarizer import SummarizerAgent
from interview_prep_qna.core.agent.write_back import WriteBackNode
from interview_prep_qna.core.config import get_settings

logger = logging.getLogger(__name__)


def build_agent_graph(
    *,
    contextualizer: ContextualizerAgent | None = None,
    router: RouterAgent | None = None,
    rag_pipeline: RAGPipeline | None = None,
    grader: GradingAgent | None = None,
    github: GitHubLiveAgent | None = None,
    web: WebSearchAgent | None = None,
    generic: GenericAgent | None = None,
    answer: AnswerAgent | None = None,
    summarizer: SummarizerAgent | None = None,
    interrogator: InterrogatorAgent | None = None,
    write_back: WriteBackNode | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Build the complete, resumable interview-preparation agent graph."""
    contextualizer = contextualizer or ContextualizerAgent()
    router = router or RouterAgent()
    rag_pipeline = rag_pipeline or RAGPipeline()
    grader = grader or GradingAgent()
    github = github or GitHubLiveAgent()
    web = web or WebSearchAgent()
    generic = generic or GenericAgent()
    answer = answer or AnswerAgent()
    summarizer = summarizer or SummarizerAgent()
    interrogator = interrogator or InterrogatorAgent()
    write_back = write_back or WriteBackNode()

    async def contextualizer_node(state: AgentState) -> AgentState:
        return await contextualizer.classify_state(state)

    async def router_node(state: AgentState) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        decision = await router.route(query, state.get("messages"))
        updated: AgentState = dict(state)
        updated["routing"] = decision.model_dump(mode="python")
        updated["current_agent"] = "router"
        updated["route"] = decision.destination.value
        return updated

    async def rag_node(state: AgentState) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        updated = await rag_pipeline.retrieve(query, state)
        updated["current_agent"] = "rag"
        updated["route"] = "grading"
        return updated

    async def grading_node(state: AgentState) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        completed_sources = {
            step.get("source") for step in state.get("escalation_steps", [])
        }
        tavily_configured = get_settings().tavily_api_key is not None
        available = [GradingAction.ANSWER, GradingAction.GENERIC]
        if "github" not in completed_sources:
            available.append(GradingAction.GITHUB)
        if (
            "web" not in completed_sources
            and "github" in completed_sources
            and tavily_configured
        ):
            available.append(GradingAction.WEB)
        stage = next(reversed(state.get("escalation_steps", [])), {}).get(
            "source", "rag"
        )
        decision = await grader.grade(
            query,
            state.get("retrieved_evidence", []),
            stage=stage,
            available_actions=tuple(available),
        )
        updated: AgentState = dict(state)
        updated["grading"] = decision.model_dump(mode="python")
        updated["current_agent"] = "grading"
        updated["route"] = decision.action.value
        logger.info(
            "graph_evidence_graded",
            extra={
                "stage": stage,
                "action": decision.action.value,
                "evidence_count": len(state.get("retrieved_evidence", [])),
            },
        )
        return updated

    async def github_node(state: AgentState) -> AgentState:
        return await _escalate(state, "github", github.search)

    async def web_node(state: AgentState) -> AgentState:
        return await _escalate(state, "web", web.search)

    async def _escalate(state: AgentState, source: str, search) -> AgentState:
        query = state.get("contextualized_query") or state.get("query")
        if not query:
            raise ValueError("state does not contain a query")
        missing = state.get("grading", {}).get("missing_information", [])
        try:
            found = await search(query, missing)
            error = None
        except Exception as exc:
            found = []
            error = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "graph_escalation_failed",
                extra={"source": source, "error_type": type(exc).__name__},
                exc_info=True,
            )
        updated: AgentState = dict(state)
        updated["retrieved_evidence"] = [
            *state.get("retrieved_evidence", []),
            *found,
        ]
        updated["escalation_steps"] = [
            *state.get("escalation_steps", []),
            {"source": source, "results": len(found), "error": error},
        ]
        updated["current_agent"] = source
        updated["route"] = "grading"
        logger.info(
            "graph_escalation_completed",
            extra={"source": source, "result_count": len(found), "failed": bool(error)},
        )
        return updated

    async def generic_node(state: AgentState) -> AgentState:
        reason = state.get("grading", {}).get("reason") or state.get(
            "routing", {}
        ).get("reason", "The query does not require knowledge-base retrieval.")
        return await generic.generate_state(state, reason)

    async def answer_node(state: AgentState) -> AgentState:
        return await answer.generate_state(state)

    async def summarizer_node(state: AgentState) -> AgentState:
        updated = await summarizer.summarize_state(state)
        updated["current_agent"] = "summarizer"
        return updated

    async def interrogator_node(state: AgentState) -> AgentState:
        if not state.get("interrogation"):
            state = await interrogator.start(state)
        session = state.get("interrogation", {})
        reply = interrupt(
            {
                "type": "interrogation",
                "phase": session.get("phase"),
                "message": state.get("response", ""),
                "questions_asked": len(session.get("questions_asked", [])),
                "max_questions": InterrogatorAgent.MAX_QUESTIONS,
            }
        )
        if isinstance(reply, dict):
            reply = reply.get("reply", reply.get("answer", ""))
        updated = await interrogator.handle_reply(state, str(reply))
        updated["current_agent"] = "interrogator"
        logger.info(
            "graph_interrogation_resumed",
            extra={
                "phase": updated.get("interrogation", {}).get("phase"),
                "route": updated.get("route"),
            },
        )
        return updated

    async def write_back_node(state: AgentState) -> AgentState:
        updated = await write_back(state)
        updated["current_agent"] = "write_back"
        return updated

    async def route_from_state(state: AgentState) -> str:
        return str(state["route"])

    graph = StateGraph(AgentState)
    graph.add_node("contextualizer", contextualizer_node)
    graph.add_node("router", router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("grading", grading_node)
    graph.add_node("github", github_node)
    graph.add_node("web", web_node)
    graph.add_node("generic", generic_node)
    graph.add_node("answer", answer_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("interrogator", interrogator_node)
    graph.add_node("write_back", write_back_node)

    graph.add_edge(START, "contextualizer")
    graph.add_edge("contextualizer", "router")
    graph.add_conditional_edges(
        "router",
        route_from_state,
        {"rag": "rag", "generic": "generic"},
    )
    graph.add_edge("rag", "grading")
    graph.add_conditional_edges(
        "grading",
        route_from_state,
        {
            "answer": "answer",
            "github": "github",
            "web": "web",
            "generic": "generic",
        },
    )
    graph.add_edge("github", "grading")
    graph.add_edge("web", "grading")
    graph.add_edge("answer", "summarizer")
    graph.add_edge("generic", "summarizer")
    graph.add_conditional_edges(
        "summarizer",
        route_from_state,
        {"complete": END, "interrogator": "interrogator"},
    )
    graph.add_conditional_edges(
        "interrogator",
        route_from_state,
        {
            "interrogator": "interrogator",
            "write_back": "write_back",
            "complete": END,
        },
    )
    graph.add_edge("write_back", END)

    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def graph_resume_config(thread_id: str) -> dict[str, Any]:
    """Return the required config for initial invocation and interrupt resumes."""
    if not thread_id.strip():
        raise ValueError("thread_id must not be empty")
    return {"configurable": {"thread_id": thread_id.strip()}}
