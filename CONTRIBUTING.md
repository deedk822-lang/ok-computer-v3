# Contributing to OK Computer v3

Thank you for your interest in contributing to OK Computer v3! This document provides guidelines and instructions for contributing to the project.

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- kubectl
- Helm 3.x
- AWS CLI (for deployment)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/ok-computer.git
   cd ok-computer
   ```

2. **Set up development environment**
   ```bash
   make dev-setup
   ```

3. **Run local development stack**
   ```bash
   make deploy-local
   ```

4. **Run tests**
   ```bash
   make test
   ```

## 📁 Project Structure

```
ok-computer/
├── services/           # Microservices
│   ├── api-gateway/   # Main API entry point
│   ├── ai-orchestrator/ # LangGraph workflows
│   └── guardrail/     # AI safety service
├── helm/              # Kubernetes deployment charts
├── scripts/           # Deployment and utility scripts
├── docs/             # Documentation
├── tests/            # Test suites
└── config/           # Configuration files
```

## 🛠️ Development Workflow

### 1. Feature Development

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Add tests for new functionality

4. Run the test suite:
   ```bash
   make test lint
   ```

5. Commit with descriptive messages:
   ```bash
   git commit -m "feat: add new guardrail detection pattern"
   ```

### 2. Coding Standards

We follow these coding standards:

- **Python**: PEP 8 with Black formatting
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions
- **Testing**: Minimum 80% code coverage
- **Linting**: Ruff for fast Python linting

### 3. Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Build process or auxiliary tool changes

## 🧪 Testing Guidelines

### Unit Tests
- Place tests in `tests/unit/`
- Use pytest for Python tests
- Mock external dependencies
- Aim for fast execution (< 1s per test)

### Integration Tests  
- Place tests in `tests/integration/`
- Test service interactions
- Use Docker containers for dependencies
- Can be slower but should complete in < 30s

### End-to-End Tests
- Place tests in `tests/e2e/`
- Test complete user workflows
- Use real or staging environments
- Should mirror production scenarios

### Running Tests

```bash
# All tests
make test

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=services tests/
```

## 📊 OpenTelemetry Instrumentation

When adding new services or modifying existing ones:

### 1. Add Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.post("/endpoint")
async def handler():
    with tracer.start_as_current_span("operation_name") as span:
        span.set_attribute("key", "value")
        # Your code here
```

### 2. Add Metrics
```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
request_counter = meter.create_counter("requests_total")

# In handler
request_counter.add(1, {"endpoint": "/api/v1/generate"})
```

### 3. Error Handling
```python
try:
    # Operation
    pass
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, str(e)))
    raise
```

## 🔒 Security Considerations

### 1. Input Validation
- Validate all user inputs
- Use Pydantic models for request/response validation
- Sanitize data before processing

### 2. Authentication & Authorization
- Use JWT tokens for API authentication
- Implement role-based access control (RBAC)
- Never log sensitive information

### 3. AI Safety
- All prompts must pass through guardrail service
- Implement content filtering for outputs
- Monitor for policy violations

## 📖 Documentation

### 1. Code Documentation
- Add docstrings to all public functions/classes
- Include parameter types and return types
- Provide usage examples for complex functions

### 2. API Documentation
- Update OpenAPI specs when changing APIs
- Include request/response examples
- Document error conditions

### 3. Architecture Documentation
- Update architecture diagrams for significant changes
- Document design decisions
- Explain integration patterns

## 🚀 Deployment & Infrastructure

### 1. Adding New Services

1. Create service directory under `services/`
2. Add Dockerfile and requirements.txt
3. Create Kubernetes manifests
4. Add to docker-compose.yml for local development
5. Update Helm charts
6. Add monitoring and health checks

### 2. Configuration Management

- Use environment variables for configuration
- Provide sensible defaults
- Document all configuration options
- Use Kubernetes ConfigMaps/Secrets

### 3. Monitoring

- Add health check endpoints
- Include Prometheus metrics
- Set up alerting rules
- Create Grafana dashboards

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Exact steps to reproduce the bug
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: OS, Python version, deployment type
6. **Logs**: Relevant log entries or error messages
7. **Trace ID**: If available from Jaeger

## 💡 Feature Requests

When requesting features:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: Your idea for implementation
3. **Alternatives**: Other solutions you've considered
4. **Impact**: Who would benefit from this feature

## 📏 Pull Request Process

1. **Ensure CI passes**: All tests and linting must pass
2. **Update documentation**: Update relevant docs
3. **Add changelog entry**: Describe your changes
4. **Request reviews**: Add at least 2 reviewers
5. **Address feedback**: Respond to review comments
6. **Squash commits**: Clean up commit history before merging

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
```

## 🎯 Performance Guidelines

### 1. Response Times
- API endpoints: < 500ms P95
- Database queries: < 100ms P95
- Cache lookups: < 10ms P95

### 2. Resource Usage
- Memory usage should be predictable
- Avoid memory leaks in long-running processes
- Use connection pooling for databases

### 3. Scalability
- Design for horizontal scaling
- Avoid global state in services
- Use async/await for I/O operations

## 🤝 Community

- **Discussions**: Use GitHub Discussions for questions
- **Chat**: Join our Discord server [link]
- **Issues**: Use GitHub Issues for bugs and features
- **Email**: team@okcomputer.dev for security issues

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Annual contributor appreciation posts

---

Thank you for contributing to OK Computer v3! 🚀
