#!/usr/bin/env python3
"""
Custom Agent Template

This is a complete, runnable example of building a Greybeard agent.
Modify this to create your own custom agent.

Usage:
    python examples/custom_agent_template.py
"""

from __future__ import annotations

from datetime import datetime
from greybeard.common import BaseAgent


class MyCustomAgent(BaseAgent):
    """
    Example custom agent that solves a specific problem.
    
    Replace "MyCustomAgent" with your agent's name,
    update the description, and implement your logic.
    """
    
    def __init__(self):
        """Initialize the agent."""
        super().__init__(
            name="my-custom-agent",
            description="Does [something specific]",
        )
    
    def run(self, user_input: str) -> dict:
        """
        Execute the agent.
        
        Args:
            user_input: Initial user question or context
            
        Returns:
            Dictionary with results
        """
        # Example 1: Interview the user
        print("\n🎯 Starting analysis...\n")
        
        self.interview.start_interview(
            opening_question=user_input,
            topic="analysis",
        )
        
        # Example 2: Gather context
        print("\n📚 Gathering context...\n")
        
        # Get more information from user
        context1 = self.interview.ask_question(
            "What's the background or context?"
        )
        
        # Accumulate in context dictionary
        self.context["background"] = context1
        
        # Example 3: Use research capability
        print("\n🔍 Researching...\n")
        
        # You can research topics
        research_summary = self.research.research_topic(
            topic=context1[:50],  # Use first 50 chars as topic
        )
        
        self.context["research"] = research_summary
        
        # Example 4: Multi-turn conversation
        print("\n💬 Deepening analysis...\n")
        
        analysis = self.multi_turn_conversation(
            initial_question="Based on what you told me, what's the core issue?",
            max_turns=5,
            expected_completion_fn=self._is_analysis_complete,
        )
        
        self.context["analysis"] = analysis
        
        # Example 5: Use LLM for synthesis
        print("\n🧠 Synthesizing findings...\n")
        
        synthesis = self.llm.call(
            system="You are an expert analyst. Synthesize the findings.",
            messages=[
                {
                    "role": "user",
                    "content": f"""
Based on this information:
- Background: {context1}
- Research: {research_summary}
- Analysis: {analysis}

Provide a comprehensive summary and recommendations.
""".strip()
                }
            ],
            temperature=0.7,
        )
        
        # Example 6: Format output
        print("\n📝 Formatting output...\n")
        
        output_doc = self.documentation.create_template(
            title="Analysis Report",
            sections={
                "Context": context1,
                "Research Summary": research_summary,
                "Detailed Analysis": analysis,
                "Synthesis & Recommendations": synthesis,
            },
            metadata={
                "timestamp": datetime.now().isoformat(),
                "agent": self.name,
                "status": "complete",
            },
        )
        
        # Example 7: Format in multiple formats
        markdown_output = self.documentation.format(
            content=output_doc,
            format_type="markdown",
        )
        
        json_output = self.documentation.format(
            content=analysis,
            format_type="json",
            metadata={"type": "analysis"},
        )
        
        # Example 8: Get conversation history
        history = self.get_conversation_history()
        
        # Return structured results
        return {
            "status": "complete",
            "user_input": user_input,
            "context": self.context.copy(),
            "analysis": analysis,
            "synthesis": synthesis,
            "markdown_report": markdown_output,
            "json_analysis": json_output,
            "conversation_turns": len(self.conversation_history),
            "conversation_summary": self.interview.summarize_interview(),
        }
    
    def _is_analysis_complete(self, response: str) -> bool:
        """
        Check if multi-turn conversation should end.
        
        Customize this logic for your agent.
        """
        # End after certain key phrases are found
        complete_indicators = ["conclusion", "final", "summary", "done"]
        return any(
            indicator in response.lower() 
            for indicator in complete_indicators
        )
    
    def get_conversation_history(self) -> list[dict]:
        """Get formatted conversation history."""
        return self.conversation_history.copy()


# Example: How to use the agent
def main():
    """Example usage of the custom agent."""
    import json
    
    print("=" * 60)
    print("🤖 Custom Agent Template Example")
    print("=" * 60)
    
    # Initialize agent
    agent = MyCustomAgent()
    
    # Run the agent
    print("\nInitializing agent...\n")
    
    # This would normally be interactive, but for example we'll use a mock
    print("""
This is a template for building custom Greybeard agents.

To use this agent:

1. Modify the class name and description
2. Implement your own run() method
3. Use the capabilities:
   - self.llm.call(...) for LLM calls
   - self.research.* for context gathering
   - self.interview.* for multi-turn conversations
   - self.documentation.* for output formatting
4. Run: python examples/custom_agent_template.py

See docs/guides/creating_agents.md for detailed documentation.
""")
    
    print("\n" + "=" * 60)
    print("Available Capabilities:")
    print("=" * 60)
    print(f"""
✅ LLM Wrapper: {agent.llm is not None}
✅ Research: {agent.research is not None}
✅ Interview: {agent.interview is not None}
✅ Documentation: {agent.documentation is not None}

All capabilities are ready to use!
    """)


if __name__ == "__main__":
    main()
