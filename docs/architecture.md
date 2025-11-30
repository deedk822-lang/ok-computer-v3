# OK Computer v3 - Architecture Overview

## System Architecture

OK Computer v3 is a distributed, cloud-native AI orchestration system designed for enterprise-grade deployments. The architecture follows microservices patterns with comprehensive observability.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   API Gateway   │    │   Guardrails    │
│                 │────▶│                 │────▶│    Service      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   LangGraph     │    │    Temporal     │
                       │  Orchestrator   │◀───┤   Workflows     │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │   PostgreSQL    │    │     KeyDB       │
│   (Hot Cache)   │    │ (Source Truth)  │    │ (Warm Cache)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. API Gateway
- **Purpose**: Entry point, authentication, routing
- **Technology**: FastAPI + OpenTelemetry
- **Features**:
  - JWT authentication
  - Request routing
  - Rate limiting
  - OpenTelemetry instrumentation

### 2. Guardrail Service  
- **Purpose**: AI safety and content policy enforcement
- **Technology**: FastAPI + Detoxify + Custom models
- **Features**:
  - Jailbreak detection
  - Toxic content filtering
  - Topic blocklists
  - NSFW classification

### 3. AI Orchestrator
- **Purpose**: Workflow orchestration and state management
- **Technology**: LangGraph + Temporal.io
- **Features**:
  - State machine workflows
  - Human-in-the-loop approvals
  - Durable execution
  - Error recovery

### 4. Observability Stack
- **Components**: 
  - OpenTelemetry (instrumentation)
  - Jaeger (distributed tracing)
  - Grafana (dashboards)
  - Prometheus (metrics)

### 5. Data Layer
- **Redis Cluster**: Hot cache (sessions, JWT, prices)
- **KeyDB**: Warm cache (metadata, URLs) 
- **PostgreSQL**: Source of truth (users, jobs, feedback)

## Data Flow

### Video Generation Request Flow

1. **Request Ingestion**
   ```
   User → Load Balancer → API Gateway → OpenTelemetry Span Created
   ```

2. **Authentication & Authorization**
   ```
   API Gateway → JWT Validation → User Context Extracted
   ```

3. **Guardrail Validation**
   ```
   API Gateway → Guardrail Service → Policy Check → Result
   ```

4. **Cost Estimation & Budget Check**
   ```
   API Gateway → Cost Calculator → Budget Service → Validation
   ```

5. **Workflow Initiation**
   ```
   API Gateway → LangGraph Orchestrator → Temporal Workflow → State Persistence
   ```

6. **Human Approval (if required)**
   ```
   Workflow → Slack Card → Human Decision → Temporal Signal
   ```

7. **AI Generation**
   ```
   Workflow → OpenRouter API → Video Generation → URL Storage
   ```

8. **Response & Feedback**
   ```
   Workflow → Response → User → Feedback → RLHF Pipeline
   ```

## Observability Architecture

### Distributed Tracing
- **Tool**: Jaeger
- **Propagation**: W3C Trace Context
- **Sampling**: 100% in dev, 10% in production
- **Retention**: 7 days

### Metrics Collection
- **Tool**: Prometheus
- **Custom Metrics**:
  - `okc_requests_total` (counter)
  - `okc_request_duration_seconds` (histogram)
  - `okc_active_workflows` (gauge)
  - `okc_feedback_rating` (histogram)

### Logging
- **Format**: Structured JSON
- **Aggregation**: Grafana Loki
- **Retention**: 30 days

## Security Architecture

### Defense in Depth

1. **Network Layer**
   - VPC isolation
   - Security groups
   - Private subnets for data layer

2. **Application Layer** 
   - JWT authentication
   - RBAC authorization
   - Input validation

3. **AI Safety Layer**
   - Jailbreak detection
   - Toxicity filtering
   - Budget controls

4. **Data Layer**
   - Encryption at rest
   - TLS in transit
   - Database access controls

## Deployment Architecture

### Kubernetes Resources

- **Namespaces**: Logical separation
  - `okc-production`: Main application
  - `observability`: Monitoring stack
  - `operators`: Infrastructure operators

- **Workloads**:
  - Deployments for stateless services
  - StatefulSets for databases
  - Jobs for batch processing

- **Networking**:
  - Services for internal communication
  - Ingress for external access
  - NetworkPolicies for security

### High Availability

- **Application Tier**: Multi-replica deployments
- **Data Tier**: Master-replica configurations
- **Cache Tier**: Cluster mode with replication
- **Monitoring**: Redundant instances

## Scalability Patterns

### Horizontal Scaling
- API Gateway: Auto-scaling based on CPU/memory
- Orchestrator: Scaled based on workflow queue depth
- Guardrails: Scaled based on request volume

### Vertical Scaling
- Database: Larger instances for complex queries
- Cache: Memory-optimized instances

### Performance Optimization
- Connection pooling
- Query optimization
- Caching strategies
- Async processing

## Disaster Recovery

### Backup Strategy
- PostgreSQL: WAL-G with S3 (30-day PITR)
- Redis: RDB snapshots to S3 (1-hour intervals)
- Application: Git-based configuration

### Recovery Procedures
- Database restoration from S3
- Cache warm-up from database
- Blue-green deployments for updates

## Integration Points

### External APIs
- OpenRouter: AI model inference
- Slack: Human-in-the-loop notifications
- AWS S3: File storage and backups

### Third-party Tools
- LocalAI: Local model inference
- Mistral Agents: Advanced AI capabilities
- Temporal: Workflow orchestration

## Performance Benchmarks

### Target SLAs
- API Response Time: P95 < 500ms
- Workflow Completion: P95 < 30s
- Uptime: 99.9%
- Error Rate: < 0.1%

### Capacity Planning
- 1000 requests/second peak
- 10,000 concurrent workflows
- 1TB data storage
- 100GB cache memory
