"""
API Gateway - Main entry point for OK Computer v3
Handles authentication, routing, and OpenTelemetry instrumentation
"""
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import httpx
import redis.asyncio as redis
import time
import os

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"),
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Create FastAPI app
app = FastAPI(
    title="OK Computer v3 - API Gateway",
    description="Enterprise AI Orchestration System",
    version="3.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Instrument FastAPI and HTTP clients
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Redis connection
redis_client = None

class VideoGenerationRequest(BaseModel):
    prompt: str
    model: str = "gpt-4o"
    user_tier: str = "pro"
    
class VideoGenerationResponse(BaseModel):
    job_id: str
    trace_id: str
    cost_estimate: float
    status: str

class FeedbackRequest(BaseModel):
    job_id: str
    rating: int  # 1 or -1
    comment: Optional[str] = None
    trace_id: str

@app.on_event("startup")
async def startup_event():
    """Initialize connections"""
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    print("✅ API Gateway started - OpenTelemetry enabled")

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup connections"""
    if redis_client:
        await redis_client.close()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token"""
    token = credentials.credentials
    # In production, verify against your auth service
    if not token.startswith("okc_"):
        raise HTTPException(401, "Invalid token")
    return {"user_id": "user_123", "tier": "pro"}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"service": "OK Computer v3", "version": "3.0.0", "status": "operational"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    with tracer.start_as_current_span("health_check") as span:
        span.set_attribute("service.name", "api-gateway")
        
        health_status = {
            "api_gateway": "healthy",
            "redis": "unknown",
            "timestamp": time.time()
        }
        
        # Check Redis connection
        try:
            await redis_client.ping()
            health_status["redis"] = "healthy"
            span.set_attribute("redis.status", "healthy")
        except Exception as e:
            health_status["redis"] = f"unhealthy: {str(e)}"
            span.set_attribute("redis.status", "unhealthy")
            span.record_exception(e)
            
        return health_status

@app.post("/v1/run", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    user_auth: Dict = Depends(verify_token)
):
    """Main video generation endpoint"""
    with tracer.start_as_current_span("video_generation_request") as span:
        span.set_attribute("user_id", user_auth["user_id"])
        span.set_attribute("user_tier", request.user_tier)
        span.set_attribute("model", request.model)
        span.set_attribute("prompt_length", len(request.prompt))
        
        trace_id = span.get_span_context().trace_id
        job_id = f"job_{int(time.time())}_{trace_id}"
        
        # Step 1: Guardrail check
        async with httpx.AsyncClient() as client:
            try:
                guardrail_response = await client.post(
                    "http://guardrail-service:8001/guardrail/scan",
                    json={"prompt": request.prompt},
                    timeout=5.0
                )
                if not guardrail_response.json().get("ok", False):
                    raise HTTPException(403, "Content policy violation")
                span.set_attribute("guardrail.status", "passed")
                
            except httpx.TimeoutException:
                span.record_exception(Exception("Guardrail timeout"))
                raise HTTPException(500, "Guardrail service timeout")
        
        # Step 2: Cost estimation
        cost_estimate = len(request.prompt) * 0.0001  # Simple cost model
        span.set_attribute("cost_estimate", cost_estimate)
        
        # Step 3: Budget check
        monthly_spend = 0.15  # Mock current spend
        user_limit = 10.0
        
        if monthly_spend + cost_estimate > user_limit:
            span.set_attribute("budget.exceeded", True)
            raise HTTPException(402, "Budget limit exceeded")
        
        span.set_attribute("budget.status", "ok")
        
        # Step 4: Queue job for processing
        job_data = {
            "job_id": job_id,
            "trace_id": str(trace_id),
            "prompt": request.prompt,
            "model": request.model,
            "user_id": user_auth["user_id"],
            "cost": cost_estimate,
            "status": "pending_approval"
        }
        
        await redis_client.hset(f"job:{job_id}", mapping=job_data)
        
        # Step 5: Trigger LangGraph workflow (async)
        # This would integrate with your Temporal workflow or direct LangGraph invocation
        
        return VideoGenerationResponse(
            job_id=job_id,
            trace_id=str(trace_id),
            cost_estimate=cost_estimate,
            status="pending_approval"
        )

@app.post("/v1/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    user_auth: Dict = Depends(verify_token)
):
    """Submit user feedback for RLHF"""
    with tracer.start_as_current_span("submit_feedback") as span:
        span.set_attribute("job_id", feedback.job_id)
        span.set_attribute("rating", feedback.rating)
        span.set_attribute("user_id", user_auth["user_id"])
        
        # Store feedback in Redis stream for ETL processing
        feedback_data = {
            "job_id": feedback.job_id,
            "rating": feedback.rating,
            "comment": feedback.comment or "",
            "trace_id": feedback.trace_id,
            "user_id": user_auth["user_id"],
            "timestamp": time.time()
        }
        
        await redis_client.xadd("feedback_stream", feedback_data)
        span.set_attribute("feedback.stored", True)
        
        return {"status": "ok", "message": "Feedback recorded"}

@app.get("/v1/job/{job_id}")
async def get_job_status(
    job_id: str,
    user_auth: Dict = Depends(verify_token)
):
    """Get job status"""
    with tracer.start_as_current_span("get_job_status") as span:
        span.set_attribute("job_id", job_id)
        
        job_data = await redis_client.hgetall(f"job:{job_id}")
        if not job_data:
            raise HTTPException(404, "Job not found")
            
        return {k.decode(): v.decode() for k, v in job_data.items()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
