#!/bin/bash
# OK Computer v3 - One-command installer
# Deploys complete AI orchestration system to EKS

set -e

CLUSTER_NAME="ok-computer-v3"
REGION="us-west-2"
K8S_VERSION="1.32"
NAMESPACE="okc-production"

echo "🎯 OK Computer v3 - Enterprise AI Orchestration System"
echo "================================================================"
echo "🚀 Starting automated deployment..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if eksctl is installed
    if ! command -v eksctl &> /dev/null; then
        log_error "eksctl is not installed. Please install from https://eksctl.io/"
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl"
        exit 1
    fi
    
    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed. Please install from https://helm.sh/"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create EKS cluster
create_eks_cluster() {
    log_info "Creating EKS cluster: $CLUSTER_NAME"
    
    # Check if cluster already exists
    if eksctl get cluster --name $CLUSTER_NAME --region $REGION &> /dev/null; then
        log_warning "Cluster $CLUSTER_NAME already exists, skipping creation"
        return
    fi
    
    cat << EOF > cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: $CLUSTER_NAME
  region: $REGION
  version: "$K8S_VERSION"

nodeGroups:
  - name: okc-workers
    instanceType: t3.medium
    desiredCapacity: 3
    minSize: 2
    maxSize: 5
    spot: true
    privateNetworking: false
    volumeSize: 30
    volumeType: gp3
    ssh:
      enableSsm: true
    tags:
      Environment: production
      Application: ok-computer-v3

addons:
  - name: aws-ebs-csi-driver
  - name: coredns
  - name: kube-proxy
  - name: vpc-cni

iam:
  withOIDC: true

EOF

    eksctl create cluster -f cluster-config.yaml
    log_success "EKS cluster created successfully"
    
    # Update kubeconfig
    aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME
    log_success "Kubeconfig updated"
}

# Install operators and dependencies
install_operators() {
    log_info "Installing operators and dependencies..."
    
    # Add Helm repositories
    helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo add postgres-operator https://opensource.zalando.com/postgres-operator/charts/postgres-operator
    helm repo add redis https://charts.bitnami.com/bitnami
    helm repo update
    
    # Create namespaces
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace operators --dry-run=client -o yaml | kubectl apply -f -
    
    # Install cert-manager (required for some operators)
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    log_success "cert-manager installed"
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
    kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
    
    # Install Jaeger
    helm install jaeger jaegertracing/jaeger \
        --namespace observability \
        --set provisionDataStore.cassandra=false \
        --set storage.type=memory \
        --set query.service.type=LoadBalancer
    log_success "Jaeger installed"
    
    # Install Grafana
    helm install grafana grafana/grafana \
        --namespace observability \
        --set adminPassword=okcomputer \
        --set service.type=LoadBalancer \
        --set persistence.enabled=true \
        --set persistence.size=10Gi
    log_success "Grafana installed"
    
    # Install PostgreSQL Operator
    helm install postgres-operator postgres-operator/postgres-operator \
        --namespace operators
    log_success "PostgreSQL operator installed"
    
    # Install Redis Cluster
    helm install redis redis/redis-cluster \
        --namespace $NAMESPACE \
        --set cluster.nodes=6 \
        --set cluster.replicas=1 \
        --set metrics.enabled=true
    log_success "Redis cluster installed"
}

# Deploy OK Computer services
deploy_okc_services() {
    log_info "Deploying OK Computer v3 services..."
    
    # Create ConfigMap for application config
    kubectl create configmap okc-config \
        --namespace=$NAMESPACE \
        --from-literal=OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger-collector.observability:4317 \
        --from-literal=OTEL_SERVICE_VERSION=3.0.0 \
        --from-literal=REDIS_URL=redis://redis-redis-cluster:6379 \
        --from-literal=DATABASE_URL=postgresql://okc:okc@postgres-primary:5432/okc \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: $NAMESPACE
  labels:
    app: api-gateway
    version: v3.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
        version: v3.0.0
    spec:
      containers:
      - name: api-gateway
        image: okcomputer/api-gateway:v3.0.0
        ports:
        - containerPort: 8000
        env:
        - name: OTEL_SERVICE_NAME
          value: "api-gateway"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: okc-config
              key: OTEL_EXPORTER_OTLP_ENDPOINT
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: okc-config
              key: REDIS_URL
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: $NAMESPACE
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: LoadBalancer
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: guardrail-service
  namespace: $NAMESPACE
  labels:
    app: guardrail-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: guardrail-service
  template:
    metadata:
      labels:
        app: guardrail-service
    spec:
      containers:
      - name: guardrail-service
        image: okcomputer/guardrail:v3.0.0
        ports:
        - containerPort: 8001
        env:
        - name: OTEL_SERVICE_NAME
          value: "guardrail-service"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: okc-config
              key: OTEL_EXPORTER_OTLP_ENDPOINT
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: guardrail-service
  namespace: $NAMESPACE
spec:
  selector:
    app: guardrail-service
  ports:
  - port: 8001
    targetPort: 8001
    protocol: TCP
EOF

    log_success "OK Computer services deployed"
}

# Wait for services to be ready
wait_for_services() {
    log_info "Waiting for services to be ready..."
    
    # Wait for deployments to be available
    kubectl wait --for=condition=available --timeout=600s \
        deployment/api-gateway deployment/guardrail-service -n $NAMESPACE
    
    # Wait for LoadBalancer services to get external IPs
    log_info "Waiting for LoadBalancer services to get external IPs..."
    for service in api-gateway; do
        while true; do
            EXTERNAL_IP=$(kubectl get svc $service -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")
            if [[ -n "$EXTERNAL_IP" && "$EXTERNAL_IP" != "null" ]]; then
                log_success "$service service ready at: $EXTERNAL_IP"
                break
            fi
            log_info "Waiting for $service LoadBalancer..."
            sleep 10
        done
    done
}

# Print service URLs
print_service_urls() {
    log_success "Deployment completed successfully! 🎉"
    echo ""
    echo "📊 Service URLs:"
    echo "================="
    
    # API Gateway
    API_URL=$(kubectl get svc api-gateway -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    echo "🎯 OK Computer API:   http://$API_URL"
    
    # Grafana
    GRAFANA_URL=$(kubectl get svc grafana -n observability -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending")
    echo "📊 Grafana:           http://$GRAFANA_URL (admin/okcomputer)"
    
    # Jaeger
    JAEGER_URL=$(kubectl get svc jaeger-query -n observability -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending")
    echo "🔍 Jaeger Tracing:    http://$JAEGER_URL:16686"
    
    echo ""
    echo "🔐 Authentication:"
    echo "=================="
    echo "Generate auth token:"
    echo "kubectl exec -n $NAMESPACE deployment/api-gateway -- curl -X POST http://localhost:8000/auth"
    echo ""
    
    echo "🧪 Run smoke test:"
    echo "=================="
    echo "curl -X POST http://$API_URL/v1/run \\"
    echo "  -H \"Authorization: Bearer okc_demo_token\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"prompt\":\"Generate a 10-second summer promo video\"}'"
    echo ""
    
    echo "✨ OK Computer v3 is now operational! ✨"
}

# Main installation flow
main() {
    log_info "Starting OK Computer v3 installation..."
    
    check_prerequisites
    create_eks_cluster
    install_operators
    deploy_okc_services
    wait_for_services
    print_service_urls
    
    log_success "Installation completed in $(date)"
}

# Handle script interruption
trap 'log_error "Installation interrupted"; exit 1' INT TERM

# Run main installation
main "$@"
