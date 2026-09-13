"""
MakiAI — Composio Skill Verification Test
Tests SkillRouter trigger matching and ComposioSkill execution flow.
"""

import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.kb.skill_router import SkillRouter
from services.cloud.composio_service import ComposioService
from skills.composio_skill import ComposioSkill
from services.ai.gemini_service import GeminiService
from services.ai.context_builder import ContextBuilder
from services.kb.kb_reader import KBReader
from services.kb.kb_writer import KBWriter


def test():
    print("=== 1. Testing SkillRouter Triggers for Composio ===")
    mock_service = ComposioService()
    kb_reader = KBReader("C:\\Knowledge-Base")
    kb_writer = KBWriter("C:\\Knowledge-Base")
    gemini = GeminiService()
    context_builder = ContextBuilder(gemini, kb_reader)
    
    skill_deps = (gemini, context_builder, kb_reader, kb_writer)
    composio_skill = ComposioSkill(*skill_deps, composio_service=mock_service)

    router = SkillRouter({
        "composio": composio_skill
    })

    test_queries = [
        "Hey Maki, create a Google Doc titled Capstone Paper Draft",
        "Check my Google Calendar for upcoming meetings",
        "Maki, check my unread emails on Gmail",
        "Create a Notion page for thesis research",
        "Maki, add a new card to my Trello board",
        "Maki, search open issues on GitHub",
    ]

    for q in test_queries:
        matched = router.detect(q)
        skill_name = "composio" if matched == composio_skill else "None"
        print(f"Query: '{q}' -> Matched: {skill_name}")
        assert matched == composio_skill, f"Failed to route query: {q}"

    print("\n=== 2. Testing ComposioSkill Execution (Graceful Guidance Mode) ===")
    response = composio_skill.execute("Create a Google Doc titled Capstone Plan")
    print("Response:\n", response)
    assert "Composio" in response or "API key" in response or "app.composio.dev" in response

    print("\n=== All Composio Skill Tests Passed Successfully! ===")


if __name__ == "__main__":
    test()
