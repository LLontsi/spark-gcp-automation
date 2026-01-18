# Documentation

Complete documentation for the Spark GCP Automation project.

## Contents

### Core Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, components, network design, and resource allocation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide with CLI and manual workflows

### Main Documentation

- **[README.md](../README.md)** - Project overview, quick start, and usage guide (located in root directory)
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines and development workflow

## Quick Links

### Getting Started

1. Read [Deployment Prerequisites](DEPLOYMENT.md#prerequisites)
2. Configure [Terraform Variables](DEPLOYMENT.md#step-1-configure-terraform-variables)
3. Deploy using [Interactive CLI](DEPLOYMENT.md#deployment-method-1-interactive-cli-recommended)

### Understanding the System

- [Network Architecture](ARCHITECTURE.md#network-architecture) - VPC, subnets, and firewall rules
- [Monitoring Stack](ARCHITECTURE.md#monitoring-architecture) - Prometheus + Grafana setup
- [Scaling Behavior](ARCHITECTURE.md#scaling-behavior) - How cluster scales from 1-N workers

### Common Tasks

- [Run WordCount Test](DEPLOYMENT.md#step-5-run-test-job)
- [Scale Cluster](DEPLOYMENT.md#step-6-scale-cluster-optional)
- [Access Monitoring](DEPLOYMENT.md#monitoring-setup)
- [Troubleshooting](DEPLOYMENT.md#troubleshooting)

## Key Features

This project provides:

- **Fully Automated Deployment** - Single command cluster deployment in ~5-6 minutes
- **Interactive CLI** - User-friendly command-line interface for all operations
- **Dynamic Scaling** - Supports 1-N workers with automatic resource calculation
- **Integrated Monitoring** - Prometheus + Grafana with pre-configured dashboards
- **Production-Ready** - Security hardening, configurable firewalls, SSH key management
- **CI/CD Integration** - Automated security scanning (tfsec, bandit, ansible-lint)

## Architecture Quick Reference

```
Components:
- Master Node: n1-standard-4 (Spark Master + Prometheus + Grafana)
- Worker Nodes: n1-standard-4 (1-N workers, dynamically scaled)
- Edge Node: n1-standard-2 (Job submission)

Software:
- Apache Spark 3.5.0 (Standalone Mode, no HDFS)
- Prometheus 2.45.0
- Grafana (latest)
- Java 11
- Python 3.x
```

## CLI Commands Reference

```bash
./manage.py                    # Start interactive CLI

# Within CLI:
deploy [-w N] [-b]            # Deploy cluster
status                         # Show cluster info
scale N                        # Scale to N workers
ssh <target>                   # SSH to node
run                           # Run WordCount test
run -u <file>                 # Upload & run custom file
logs                          # View deployment logs
destroy                       # Clean up resources
```

## Monitoring Access

After deployment, access dashboards at:

- **Spark Master UI**: `http://MASTER_IP:8080`
- **Grafana**: `http://MASTER_IP:3000` (admin/admin)
- **Prometheus**: `http://MASTER_IP:9090`

## Cost Information

**Estimated Cost** (running 24/7):
- 2-Worker Cluster: ~$630/month
- 3-Worker Cluster: ~$810/month

**GCP Free Trial**: $300 credit covers ~2 weeks continuous or several months of testing

**Recommendation**: Use `destroy` command when not testing to save credits

## Support & Contributions

- Report issues on GitHub
- Submit pull requests for improvements
- Follow [Contributing Guidelines](../CONTRIBUTING.md)

## Authors

- **LONTSIE LAMBOU Ronaldinho**
- **LADO SAHA**

## License

MIT License - See [LICENSE](../LICENSE) file
