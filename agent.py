"""
Agent: Main Orchestration with Streaming and Tool Use

FDE-Level Concepts Demonstrated:
1. Tool use loop (User → Claude → Tool → Claude → Response)
2. Streaming responses for real-time feedback
3. Proper error handling and recovery
4. Structured output enforcement
5. Integration of all components
"""

import json
import asyncio
from typing import Generator, AsyncGenerator, Optional
from dataclasses import dataclass

import anthropic

from config import CLAUDE_MODEL, validate_config
from prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES, build_messages
from guardrails import GuardrailsPipeline, PolicyResponse, should_escalate
from embeddings import search_policies, get_policy_index

# =============================================================================
# Tool Definitions for Claude API
# =============================================================================

# FDE Note: These must match the MCP server tools exactly
TOOLS = [
    {
        "name": "policy_get_employee_info",
        "description": "Retrieve employee information including level, title, and department. Use this to determine an employee's corporate level before checking policy permissions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID (e.g., 'emp001', 'emp002')",
                    "pattern": "^emp\\d{3}$"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json",
                    "description": "Output format preference"
                }
            },
            "required": ["employee_id"]
        }
    },
    {
        "name": "policy_search_manual",
        "description": "Search the corporate policy manual for relevant sections. Returns confidence scores - if confidence is low, say 'I don't have enough information.'",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about company policy",
                    "minLength": 3,
                    "maxLength": 500
                },
                "max_results": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of policy sections to return"
                },
                "response_format": {
                    "type": "string",
                    "enum": ["json", "markdown"],
                    "default": "json"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "policy_check_approval_threshold",
        "description": "Determine the approval requirements for an expense based on amount and employee level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employee_id": {
                    "type": "string",
                    "description": "Employee ID requesting the expense",
                    "pattern": "^emp\\d{3}$"
                },
                "amount": {
                    "type": "number",
                    "description": "Expense amount in USD",
                    "minimum": 0,
                    "maximum": 1000000
                },
                "expense_type": {
                    "type": "string",
                    "description": "Type of expense (e.g., 'travel', 'software', 'equipment')"
                }
            },
            "required": ["employee_id", "amount", "expense_type"]
        }
    }
]


# =============================================================================
# Tool Execution
# =============================================================================

# Import mock database from MCP server
from mcp_server import EMPLOYEE_DATABASE

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Execute a tool and return the result.
    
    FDE Note: In production with MCP, this would call the MCP server.
    For direct API usage, we execute locally.
    """
    if tool_name == "policy_get_employee_info":
        employee_id = tool_input.get("employee_id")
        response_format = tool_input.get("response_format", "json")
        
        employee = EMPLOYEE_DATABASE.get(employee_id)
        if not employee:
            return json.dumps({"error": f"Employee '{employee_id}' not found"})
        
        if response_format == "json":
            return json.dumps(employee, indent=2)
        else:
            return f"Employee: {employee['name']}, Level: {employee['level']}, Title: {employee['title']}"
    
    elif tool_name == "policy_search_manual":
        query = tool_input.get("query")
        max_results = tool_input.get("max_results", 3)
        
        results, is_confident = search_policies(query)
        return json.dumps({
            "query": query,
            "is_confident": is_confident,
            "results": results[:max_results]
        }, indent=2)
    
    elif tool_name == "policy_check_approval_threshold":
        employee_id = tool_input.get("employee_id")
        amount = tool_input.get("amount")
        expense_type = tool_input.get("expense_type")
        
        employee = EMPLOYEE_DATABASE.get(employee_id)
        if not employee:
            return json.dumps({"error": f"Employee '{employee_id}' not found"})
        
        # Determine approval level
        if amount < 500:
            required_level = "Direct Manager"
            min_level = employee["level"] + 1
        elif amount < 2000:
            required_level = "Department Head"
            min_level = 7
        elif amount < 10000:
            required_level = "VP"
            min_level = 11
        else:
            required_level = "CFO"
            min_level = 13
        
        return json.dumps({
            "employee": {
                "id": employee["id"],
                "name": employee["name"],
                "level": employee["level"]
            },
            "expense": {
                "amount": amount,
                "type": expense_type,
                "formatted_amount": f"${amount:,.2f}"
            },
            "approval_requirements": {
                "required_approver_level": required_level,
                "minimum_approver_level_number": min_level,
                "can_self_approve": False,
                "reason": "Self-approval prohibited per policy approval-002"
            }
        }, indent=2)
    
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# =============================================================================
# Streaming Agent
# =============================================================================

@dataclass
class AgentResponse:
    """Final response from the agent."""
    raw_response: str
    structured_response: Optional[PolicyResponse]
    tool_calls: list[dict]
    error: Optional[str] = None


class PolicyAgent:
    """
    Main agent that orchestrates the policy enforcement workflow.
    
    FDE-Level Features:
    - Tool use loop with proper state management
    - Streaming for real-time feedback
    - Guardrails integration
    - Structured output validation
    """
    
    def __init__(self):
        validate_config()
        self.client = anthropic.Anthropic()
        self.guardrails = GuardrailsPipeline()
        self.model = CLAUDE_MODEL
        
        # Pre-initialize the policy index
        get_policy_index()
    
    def run(self, user_query: str) -> AgentResponse:
        """
        Run the agent on a user query (non-streaming).
        
        Args:
            user_query: The user's policy question
            
        Returns:
            AgentResponse with the decision
        """
        # Validate input
        validation = self.guardrails.validate_input(user_query)
        if not validation.is_valid:
            return AgentResponse(
                raw_response="",
                structured_response=None,
                tool_calls=[],
                error=validation.error_message
            )
        
        # Build messages with few-shot examples
        messages = build_messages(validation.sanitized_input)
        tool_calls = []
        
        # Tool use loop
        max_iterations = 10  # Prevent infinite loops
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )
            
            # Check if we're done (no more tool calls)
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                
                return self._process_final_response(final_text, tool_calls)
            
            # Process tool calls
            if response.stop_reason == "tool_use":
                # Add assistant's response to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Execute each tool call
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        
                        # Execute tool
                        result = execute_tool(tool_name, tool_input)
                        
                        tool_calls.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "output": result
                        })
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                
                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
        
        return AgentResponse(
            raw_response="",
            structured_response=None,
            tool_calls=tool_calls,
            error="Maximum iterations reached without final response"
        )
    
    def run_streaming(self, user_query: str) -> Generator[str, None, AgentResponse]:
        """
        Run the agent with streaming output.
        
        Yields text chunks as they arrive, then returns final AgentResponse.
        
        FDE Note: Streaming is critical for UX in production systems.
        Users need feedback that the system is working, especially
        when tool calls take time.
        """
        # Validate input
        validation = self.guardrails.validate_input(user_query)
        if not validation.is_valid:
            yield f"Error: {validation.error_message}"
            return AgentResponse(
                raw_response="",
                structured_response=None,
                tool_calls=[],
                error=validation.error_message
            )
        
        messages = build_messages(validation.sanitized_input)
        tool_calls = []
        accumulated_text = ""
        
        max_iterations = 10
        for iteration in range(max_iterations):
            # Stream the response
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            ) as stream:
                current_text = ""
                tool_use_blocks = []
                
                for event in stream:
                    # Handle text streaming
                    if hasattr(event, 'type'):
                        if event.type == 'content_block_delta':
                            if hasattr(event.delta, 'text'):
                                chunk = event.delta.text
                                current_text += chunk
                                accumulated_text += chunk
                                yield chunk
                
                # Get the final message
                response = stream.get_final_message()
                
                # Check stop reason
                if response.stop_reason == "end_turn":
                    return self._process_final_response(accumulated_text, tool_calls)
                
                # Handle tool use
                if response.stop_reason == "tool_use":
                    messages.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            yield f"\n[Calling tool: {block.name}...]\n"
                            
                            result = execute_tool(block.name, block.input)
                            
                            tool_calls.append({
                                "tool": block.name,
                                "input": block.input,
                                "output": result
                            })
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result
                            })
                    
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
        
        return AgentResponse(
            raw_response=accumulated_text,
            structured_response=None,
            tool_calls=tool_calls,
            error="Maximum iterations reached"
        )
    
    def _process_final_response(
        self, 
        response_text: str, 
        tool_calls: list[dict]
    ) -> AgentResponse:
        """Process and validate the final response."""
        # Try to extract JSON from the response
        json_match = None
        try:
            # Look for JSON block in markdown code fence
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
                is_valid, structured, error = self.guardrails.validate_output(json_str)
                if is_valid:
                    return AgentResponse(
                        raw_response=response_text,
                        structured_response=structured,
                        tool_calls=tool_calls
                    )
        except Exception as e:
            pass
        
        # Return raw response if structured parsing fails
        return AgentResponse(
            raw_response=response_text,
            structured_response=None,
            tool_calls=tool_calls
        )


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Interactive CLI for the policy agent."""
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    
    console = Console()
    agent = PolicyAgent()
    
    console.print(Panel.fit(
        "[bold blue]Corporate Policy Assistant[/bold blue]\n"
        "Ask questions about travel, expenses, and approvals.\n"
        "Type 'quit' to exit.",
        title="Welcome"
    ))
    
    while True:
        console.print()
        user_input = console.input("[bold green]You:[/bold green] ")
        
        if user_input.lower() in ["quit", "exit", "q"]:
            console.print("[yellow]Goodbye![/yellow]")
            break
        
        if not user_input.strip():
            continue
        
        console.print("\n[bold blue]Assistant:[/bold blue]")
        
        # Run with streaming
        final_response = None
        for chunk in agent.run_streaming(user_input):
            if isinstance(chunk, AgentResponse):
                final_response = chunk
            else:
                console.print(chunk, end="")
        
        console.print()
        
        # Show structured response if available
        if final_response and final_response.structured_response:
            sr = final_response.structured_response
            status = "[green]✓ APPROVED[/green]" if sr.approved else "[red]✗ NOT APPROVED[/red]"
            console.print(Panel(
                f"{status}\n"
                f"[bold]Confidence:[/bold] {sr.confidence:.0%}\n"
                f"[bold]Policy:[/bold] {sr.policy_reference}\n"
                f"[bold]Escalation:[/bold] {'Required' if sr.requires_escalation else 'Not required'}",
                title="Decision Summary"
            ))


if __name__ == "__main__":
    main()
