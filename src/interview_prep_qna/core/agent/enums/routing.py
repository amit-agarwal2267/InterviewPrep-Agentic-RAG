from enum import StrEnum


class AgentRoute(StrEnum):
    CONTEXTUALIZER = "contextualizer"
    ROUTER = "router"
    RAG = "rag"
    GRADING = "grading"
    GITHUB = "github"
    WEB = "web"
    GENERIC = "generic"
    ANSWER = "answer"
    SUMMARIZER = "summarizer"
    INTERROGATOR = "interrogator"
    WRITE_BACK = "write_back"
    COMPLETE = "complete"
    ERROR = "error"


class QueryRoute(StrEnum):
    GENERIC = "generic"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"


class RouteDestination(StrEnum):
    RAG = "rag"
    GENERIC = "generic"
