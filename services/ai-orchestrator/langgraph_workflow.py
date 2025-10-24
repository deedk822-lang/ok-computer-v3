"""
LangGraph Workflow - State machine orchestration with human-in-the-loop
Integrates with Temporal.io for durable execution
"""
from typing import TypedDict, Optional, Literal, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import httpx
import time
import json
import os

# OpenTelemetry
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

class VideoState(TypedDict):
    """State for video generation workflow"""
    job_id: str
    prompt: str
    model: str
    cost: float
    video_url: Optional[str]
    human_approval: Optional[Literal["approve", "reject", "edit"]]
    trace_id: str
    user_id: str
    user_tier: str
    error_message: Optional[str]
    retry_count: int

class VideoWorkflow:
    """LangGraph workflow for video generation with human approval"""
    
    def __init__(self):
        self.setup_workflow()
    
    async def cost_estimation_node(self, state: VideoState) -> Dict[str, Any]:
        """Calculate cost based on model and prompt complexity"""
        with tracer.start_as_current_span("cost_estimation") as span:
            span.set_attribute("prompt_length", len(state["prompt"]))
            span.set_attribute("model", state["model"])
            
            # Advanced cost calculation
            base_cost = 0.10
            prompt_multiplier = len(state["prompt"]) / 1000
            model_multipliers = {
                "gpt-4o": 1.5,
                "gpt-4": 1.2,
                "gpt-3.5-turbo": 0.8,
                "claude-3": 1.3
            }
            
            model_mult = model_multipliers.get(state["model"], 1.0)
            total_cost = base_cost * (1 + prompt_multiplier) * model_mult
            
            span.set_attribute("calculated_cost", total_cost)
            
            return {"cost": round(total_cost, 4)}
    
    async def guardrail_check_node(self, state: VideoState) -> Dict[str, Any]:
        """Pre-generation guardrail validation"""
        with tracer.start_as_current_span("guardrail_check") as span:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        "http://guardrail-service:8001/guardrail/scan",
                        json={"prompt": state["prompt"]}
                    )
                    
                    result = response.json()
                    
                    if not result.get("ok", False):
                        span.set_attribute("guardrail.violation", True)
                        return {
                            "error_message": f"Guardrail violation: {result.get('reason', 'Unknown')}"
                        }
                    
                    span.set_attribute("guardrail.passed", True)
                    return {}
                    
            except Exception as e:
                span.record_exception(e)
                return {"error_message": f"Guardrail check failed: {str(e)}"}
    
    async def budget_check_node(self, state: VideoState) -> Dict[str, Any]:
        """Validate user budget limits"""
        with tracer.start_as_current_span("budget_check") as span:
            # Mock budget service - in production, call actual budget API
            monthly_spend = 2.50  # Mock current spend
            
            limits = {
                "free": 5.0,
                "pro": 50.0,
                "enterprise": 500.0
            }
            
            user_limit = limits.get(state["user_tier"], 5.0)
            
            if monthly_spend + state["cost"] > user_limit:
                span.set_attribute("budget.exceeded", True)
                return {
                    "error_message": f"Budget limit exceeded. Monthly: ${monthly_spend:.2f}, Limit: ${user_limit:.2f}"
                }
            
            # Alert at 80% usage
            if (monthly_spend + state["cost"]) / user_limit > 0.8:
                await self.send_budget_alert(state["user_id"], monthly_spend, user_limit)
            
            span.set_attribute("budget.ok", True)
            return {}
    
    async def send_slack_approval_card(self, state: VideoState) -> Dict[str, Any]:
        """Send interactive Slack card for human approval"""
        with tracer.start_as_current_span("slack_approval_card") as span:
            # Mock Slack integration - in production, use Slack SDK
            card_data = {
                "job_id": state["job_id"],
                "prompt": state["prompt"][:200] + "..." if len(state["prompt"]) > 200 else state["prompt"],
                "cost": state["cost"],
                "user_tier": state["user_tier"],
                "trace_id": state["trace_id"]
            }
            
            # In production: Send actual Slack BlockKit card
            print(f"🎯 Slack Approval Card Sent: {json.dumps(card_data, indent=2)}")
            
            span.set_attribute("slack.card_sent", True)
            return {"slack_card_sent": True}
    
    async def human_approval_node(self, state: VideoState) -> Dict[str, Any]:
        """Wait for human approval via Slack or UI"""
        with tracer.start_as_current_span("human_approval_gate") as span:
            # Send Slack card
            await self.send_slack_approval_card(state)
            
            # In production: This would be an interrupt that waits for external signal
            # For demo: simulate approval after 2 seconds
            await asyncio.sleep(2)
            
            # Mock approval decision (in production: comes from Slack webhook or UI)
            approval = "approve"  # Could be "approve", "reject", "edit"
            
            span.set_attribute("human_approval", approval)
            return {"human_approval": approval}
    
    async def video_generation_node(self, state: VideoState) -> Dict[str, Any]:
        """Generate video using AI model"""
        with tracer.start_as_current_span("video_generation") as span:
            span.set_attribute("model", state["model"])
            
            # Mock video generation - in production: call OpenRouter/OpenAI
            await asyncio.sleep(3)  # Simulate generation time
            
            video_url = f"https://storage.okc.dev/videos/{state['job_id']}.mp4"
            
            span.set_attribute("video_generated", True)
            span.set_attribute("video_url", video_url)
            
            return {"video_url": video_url}
    
    async def send_budget_alert(self, user_id: str, current_spend: float, limit: float):
        """Send budget warning alert"""
        # Mock alert - in production: integrate with notification service
        print(f"⚠️ Budget Alert: User {user_id} at {(current_spend/limit)*100:.1f}% of limit")
    
    def route_after_approval(self, state: VideoState) -> str:
        """Route based on human approval decision"""
        approval = state.get("human_approval")
        
        if approval == "approve":
            return "generate_video"
        elif approval == "edit":
            return "cost_estimation"  # Loop back for re-estimation
        else:  # reject
            return END
    
    def route_after_checks(self, state: VideoState) -> str:
        """Route after guardrail and budget checks"""
        if state.get("error_message"):
            return END  # Terminate on errors
        return "human_approval"
    
    def setup_workflow(self):
        """Configure the LangGraph state machine"""
        workflow = StateGraph(VideoState)
        
        # Add nodes
        workflow.add_node("cost_estimation", self.cost_estimation_node)
        workflow.add_node("guardrail_check", self.guardrail_check_node)
        workflow.add_node("budget_check", self.budget_check_node)
        workflow.add_node("human_approval", self.human_approval_node)
        workflow.add_node("generate_video", self.video_generation_node)
        
        # Define flow
        workflow.set_entry_point("cost_estimation")
        workflow.add_edge("cost_estimation", "guardrail_check")
        workflow.add_edge("guardrail_check", "budget_check")
        workflow.add_conditional_edges("budget_check", self.route_after_checks)
        workflow.add_conditional_edges("human_approval", self.route_after_approval)
        workflow.add_edge("generate_video", END)
        
        # Compile with memory for state persistence
        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)
    
    async def run_workflow(self, initial_state: VideoState) -> VideoState:
        """Execute the complete workflow"""
        with tracer.start_as_current_span("video_workflow") as span:
            span.set_attribute("job_id", initial_state["job_id"])
            span.set_attribute("user_id", initial_state["user_id"])
            
            config = {"configurable": {"thread_id": initial_state["job_id"]}}
            
            try:
                result = await self.app.ainvoke(initial_state, config)
                span.set_attribute("workflow.completed", True)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("workflow.error", str(e))
                raise

# Example usage
async def main():
    """Demo workflow execution"""
    workflow = VideoWorkflow()
    
    initial_state = VideoState(
        job_id="job_123456789",
        prompt="Generate a 10-second summer promo video with upbeat music",
        model="gpt-4o",
        cost=0.0,
        video_url=None,
        human_approval=None,
        trace_id="trace_123456789",
        user_id="user_pro_123",
        user_tier="pro",
        error_message=None,
        retry_count=0
    )
    
    print("🚀 Starting video generation workflow...")
    result = await workflow.run_workflow(initial_state)
    print("✅ Workflow completed!")
    print(f"Final state: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
