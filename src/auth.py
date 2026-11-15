"""Trusted, in-process mock identity for the POC, never an HTTP login service.

Only application bootstrap may issue sessions. Learner requests cannot select
an identity, role, learner ID, thread ID, or review scope. This simulates an
identity provider; it does not authenticate real people or resist host access.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import secrets


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    learner_id: str | None = None
    review_scope: frozenset[str] = frozenset()


_IDENTITY: ContextVar[Principal | None] = ContextVar("sprints_identity", default=None)
_REVIEW: ContextVar[dict | None] = ContextVar("sprints_review", default=None)


def current_principal() -> Principal:
    p = _IDENTITY.get()
    if p is None:
        raise AuthorizationError("Authenticated application session required")
    return p


def require_learner(learner_id: str | None = None) -> str:
    p = current_principal()
    if p.role != "learner" or not p.learner_id:
        raise AuthorizationError("Learner authorization required")
    if learner_id is not None and learner_id.strip().upper() != p.learner_id:
        raise AuthorizationError("Access to another learner is forbidden")
    return p.learner_id


def require_review(pending_id: str, digest: str, decision: dict) -> str:
    p = current_principal()
    cap = _REVIEW.get()
    if p.role != "reviewer" or not cap or cap != {
        "pending_id": pending_id, "digest": digest, "decision": decision,
    }:
        raise AuthorizationError("Trusted, bound human review required")
    return p.subject


class MockIdentityProvider:
    """Local application bootstrap fixture. Never expose issuance to learners."""

    def __init__(self):
        self.__sessions: dict[str, Principal] = {}
        self.__accounts = {
            f"learner-{n}": Principal(f"mock-student-{n}", "learner", f"SPR-{n}")
            for n in range(1001, 1026)
        }
        self.__accounts["career-reviewer"] = Principal(
            "mock-career-reviewer", "reviewer", review_scope=frozenset({f"SPR-{n}" for n in range(1001, 1026)}))
        self.__accounts["unassigned-reviewer"] = Principal("mock-unassigned-reviewer", "reviewer")

    def issue_mock_session(self, account: str) -> str:
        """Trusted bootstrap only: the caller is the local application operator."""
        if account not in self.__accounts:
            raise AuthorizationError("Unknown mock account")
        token = secrets.token_urlsafe(32)
        self.__sessions[token] = self.__accounts[account]
        return token

    def resolve(self, token: str) -> Principal:
        if not isinstance(token, str) or token not in self.__sessions:
            raise AuthorizationError("Invalid application session")
        return self.__sessions[token]

    @contextmanager
    def bind(self, token: str, review: dict | None = None):
        principal = self.resolve(token)
        it = _IDENTITY.set(principal)
        rt = _REVIEW.set(review)
        try:
            yield principal
        finally:
            _REVIEW.reset(rt)
            _IDENTITY.reset(it)
