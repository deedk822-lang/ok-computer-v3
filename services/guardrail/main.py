"""
Guardrail Service - AI Safety and Content Policy Enforcement
Detects jailbreaks, toxic content, and policy violations
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import re
import os
import asyncio

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# AI Safety Models
try:
    from detoxify import Detoxify
    DETOXIFY_AVAILABLE = True
except ImportError:
    DETOXIFY_AVAILABLE = False
    print("⚠️ Detoxify not available - using mock toxic detection")

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"),
    insecure=True
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

app = FastAPI(
    title="OK Computer v3 - Guardrail Service",
    description="AI Safety and Content Policy Enforcement",
    version="3.0.0"
)

FastAPIInstrumentor.instrument_app(app)

class GuardrailRequest(BaseModel):
    prompt: str
    
class GuardrailResponse(BaseModel):
    ok: bool
    reason: str = ""
    confidence: float = 0.0
    violations: list = []

class GuardrailService:
    """AI Guardrail implementation with multiple safety layers"""
    
    def __init__(self):
        # Initialize toxicity detector
        if DETOXIFY_AVAILABLE:
            self.detoxify = Detoxify('original')
        else:
            self.detoxify = None
            
        # Jailbreak detection patterns
        self.jailbreak_patterns = [
            r"ignore.*(above|previous|prior).*instruct",
            r"disregard.*(system|prompt)",
            r"act as.*DAN",
            r"forget.*instructions",
            r"pretend.*you.*are",
            r"roleplay.*as",
            r"simulate.*being",
        ]
        
        # Topic blocklist
        self.topic_blocklist = [
            "violence", "illegal", "nsfw", "harmful", "dangerous",
            "weapons", "drugs", "hate", "harassment", "bullying"
        ]
        
        # Suspicious prompt indicators
        self.suspicious_indicators = [
            "bypass", "override", "circumvent", "hack", "exploit",
            "vulnerability", "backdoor", "injection", "privilege"
        ]
    
    def detect_jailbreak(self, prompt: str) -> Dict[str, Any]:
        """Detect jailbreak attempts"""
        violations = []
        
        for i, pattern in enumerate(self.jailbreak_patterns):
            if re.search(pattern, prompt, re.IGNORECASE):
                violations.append({
                    "type": "jailbreak", 
                    "pattern_id": i,
                    "pattern": pattern,
                    "confidence": 0.9
                })
        
        return {
            "violations": violations,
            "detected": len(violations) > 0
        }
    
    def detect_toxic_content(self, prompt: str) -> Dict[str, Any]:
        """Detect toxic content using Detoxify or fallback"""
        if self.detoxify:
            try:
                results = self.detoxify.predict(prompt)
                max_score = max(results.values())
                
                if max_score > 0.8:
                    return {
                        "detected": True,
                        "confidence": float(max_score),
                        "scores": {k: float(v) for k, v in results.items()}
                    }
            except Exception as e:
                print(f"Detoxify error: {e}")
        
        # Fallback: simple keyword matching
        toxic_keywords = ["kill", "murder", "suicide", "harm", "hurt", "violence"]
        detected_keywords = [kw for kw in toxic_keywords if kw in prompt.lower()]
        
        if detected_keywords:
            return {
                "detected": True,
                "confidence": 0.7,
                "keywords": detected_keywords
            }
        
        return {"detected": False, "confidence": 0.0}
    
    def check_topic_blocklist(self, prompt: str) -> Dict[str, Any]:
        """Check against topic blocklist"""
        violations = []
        
        for topic in self.topic_blocklist:
            if topic in prompt.lower():
                violations.append({
                    "type": "blocked_topic",
                    "topic": topic,
                    "confidence": 0.8
                })
        
        return {
            "violations": violations,
            "detected": len(violations) > 0
        }
    
    def detect_suspicious_behavior(self, prompt: str) -> Dict[str, Any]:
        """Detect suspicious prompting behavior"""
        violations = []
        
        for indicator in self.suspicious_indicators:
            if indicator in prompt.lower():
                violations.append({
                    "type": "suspicious_behavior",
                    "indicator": indicator,
                    "confidence": 0.6
                })
        
        return {
            "violations": violations,
            "detected": len(violations) > 0
        }
    
    def scan(self, prompt: str) -> GuardrailResponse:
        """Comprehensive prompt scanning"""
        all_violations = []
        
        # Run all checks
        jailbreak_result = self.detect_jailbreak(prompt)
        if jailbreak_result["detected"]:
            all_violations.extend(jailbreak_result["violations"])
        
        toxic_result = self.detect_toxic_content(prompt)
        if toxic_result["detected"]:
            all_violations.append({
                "type": "toxic_content",
                "confidence": toxic_result["confidence"],
                "details": toxic_result
            })
        
        topic_result = self.check_topic_blocklist(prompt)
        if topic_result["detected"]:
            all_violations.extend(topic_result["violations"])
        
        suspicious_result = self.detect_suspicious_behavior(prompt)
        if suspicious_result["detected"]:
            all_violations.extend(suspicious_result["violations"])
        
        # Determine overall result
        if all_violations:
            max_confidence = max(v.get("confidence", 0.0) for v in all_violations)
            primary_violation = max(all_violations, key=lambda x: x.get("confidence", 0.0))
            
            return GuardrailResponse(
                ok=False,
                reason=f"Policy violation: {primary_violation['type']}",
                confidence=max_confidence,
                violations=all_violations
            )
        
        return GuardrailResponse(
            ok=True,
            reason="No policy violations detected",
            confidence=1.0,
            violations=[]
        )

# Initialize guardrail service
guardrail_service = GuardrailService()

@app.post("/guardrail/scan", response_model=GuardrailResponse)
async def scan_prompt(request: GuardrailRequest):
    """Scan prompt for policy violations"""
    with tracer.start_as_current_span("guardrail_scan") as span:
        span.set_attribute("prompt_length", len(request.prompt))
        
        result = guardrail_service.scan(request.prompt)
        
        span.set_attribute("guardrail.passed", result.ok)
        span.set_attribute("guardrail.confidence", result.confidence)
        span.set_attribute("guardrail.violations_count", len(result.violations))
        
        if not result.ok:
            span.set_attribute("guardrail.reason", result.reason)
        
        return result

@app.get("/")
async def root():
    return {"service": "guardrail", "status": "operational", "version": "3.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "service": "guardrail",
        "status": "healthy",
        "detoxify_available": DETOXIFY_AVAILABLE,
        "patterns_loaded": len(guardrail_service.jailbreak_patterns)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
