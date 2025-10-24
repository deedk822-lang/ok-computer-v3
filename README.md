# OK Computer v3 - Mission-Control System

Enterprise-grade AI orchestration system with bullet-proof observability, self-improving feedback loops, and production-ready deployment.

## 🎯 Features

- **OpenTelemetry Observability**: Full distributed tracing across all services
- **LangGraph Orchestration**: State-machine workflows with human-in-the-loop
- **RLHF Feedback Loop**: Thumbs become training gold for continuous improvement  
- **Distributed State**: Redis/KeyDB/PostgreSQL with high availability
- **AI Guardrails**: Dual-layer defense against jailbreaks and policy violations
- **One-Command Deploy**: Complete EKS deployment in 5 minutes
- **30-Second Smoke Test**: Production readiness validation

## 🚀 Quick Start

```bash
curl -sSL https://raw.githubusercontent.com/your-org/ok-computer/v3/install.sh | bash
```

## 📊 Architecture

![Architecture](docs/architecture.png)

The system consists of 8 core components:

1. **Observability Stack** - OpenTelemetry + Jaeger + Grafana
2. **AI Orchestrator** - LangGraph state machines with Temporal.io
3. **Feedback Engine** - RLHF training pipeline with LoRA adapters  
4. **Distributed State** - Redis Cluster + KeyDB + Patroni PostgreSQL
5. **Security Layer** - Guardrails + Budget controls + NSFW detection
6. **Installer** - Automated EKS deployment with Helm charts
7. **Monitoring** - Real-time dashboards and alerting
8. **Integration Hub** - LocalAI + Mistral Agents + 50+ connectors

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🔧 Development

```bash
git clone https://github.com/your-org/ok-computer.git
cd ok-computer
make dev-setup
make test
```

## 📦 Helm Charts

Deploy individual components:

```bash
helm install okc-observability ./helm/observability
helm install okc-orchestrator ./helm/orchestrator  
helm install okc-cache ./helm/cache
```

## 🎪 LocalAI & Mistral Integration

Supports 50+ integrations including:
- AnythingLLM, FlowiseAI, LangChain4j
- Wave Terminal, Big AGI, LLPhant  
- Mistral Agents API with tools and conversations
- Document understanding and OCR processing

## 📈 Monitoring & Alerts

- **Grafana Dashboards**: Performance, cost, usage metrics
- **Jaeger Traces**: End-to-end request tracing  
- **Slack Alerts**: P95 latency, budget limits, policy violations
- **Feedback Analytics**: Thumbs-up rates and model performance

## 🏗️ Production Checklist

- [ ] Jaeger waterfall shows full trace
- [ ] LangGraph human node pauses workflow  
- [ ] Thumbs-up increments Grafana gauge
- [ ] PostgreSQL holds ≥ 1 feedback row
- [ ] Guardrail blocks jailbreak attempts
- [ ] Budget hard-stop tested
- [ ] Install script works on fresh EC2

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing  

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

**Built for production. Battle-tested at scale. Ready to deploy.** 🚀
