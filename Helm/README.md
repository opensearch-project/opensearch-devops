# OpenSearch Helm
A Helm chart for deploying an configurable highly available Opensearch cluster.

## Current Features
- Deploys a scalable number of Opensearch master nodes
- Configurable and scalable number of Opensearch nodes
  - A `node` object is defined in the `values.yaml` as an array, as many node types or variations can be generated as desired. 
- Node objects can have the following roles assigned the following roles:
  - master - Allows additional masters if desired
  - data - This can be further broken down into various tiers:
    - data_content
    - data_hot 
    - data_warm
    - data_cold
    - data_frozen
  - ingest - Client facing nodes
  - remote_cluster_client - Cross-Cluster query


## Future Features
- Ingress management
- Privileged Daemonset for configuring required settings such as vm.max_map_count
  - Running this standalone means there is no privilege exposure in the Opensearch runtimes
- RBAC for the Opensearch runtimes  
- Authentication and Authorization configuration via the Helm Chart:
  - LDAP
  - SAML
  - OIDC
- Pre-set health checks:
  - Liveness Probes
  - Readiness Probes
- Pre-set Affinity rules:
  - Soft or hard anti-affinities
- Cert-Manager integration:
  - Pre-installed or new installation for managing Opensearch TLS
- Prometheus 
  - Chart installed exporter with configuration available
  - Optional Grafana deployment

---

## Getting Started

### Host Pre-Requisites
1. Set the `vm.max_map_count` to 262144, via `sysctl vm.max_map_count=262144` or editing `/etc/sysctl.conf`

### Kubernetes Pre-Requisites
1. Certificate objects created if not using Cert-Manager (TBD), see TLS Guide below for an openssl demonstration.

### Deployment
1. Create the namespace `kubectl create namespace <OPENSEARCH_NAMESPACE>`
2. Clone the repository `git clone https://github.com/iron-rain/opensearch-devops.git`
3. `cd opensearch-devops/Helm`
4. `helm upgrade --install opensearch ./ -n <OPENSEARCH_NAMESPACE>`

---

## Examples
1. OpenSSL Certificate Generation

    ### Create the Root CA
    `openssl genrsa -des3 -out ca.key 2048`

    `openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt -subj "/CN=opensearch"`

    ### Transport Certificates
    `openssl req -out transport.csr -newkey rsa:2048 -nodes -keyout transport.key -subj "/CN=nodes"`

    `openssl x509 -req -in transport.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out transport.crt -days 365 -sha256`

    `kubectl create secret generic transport-tls --from=file=tls.crt=./transport.crt --from-file=tls.key=./transport.key --from-file=ca.crt=./ca.crt -n <OPENSEARCH_NAMESPACE>`

    ### Rest Certificates
    `openssl req -out rest.csr -newkey rsa:2048 -nodes -keyout rest.key -subj "/CN=rest"`

    `openssl x509 -req -in rest.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out rest.crt -days 365 -sha256`

    `kubectl create secret generic rest-tls --from-file=tls.crt=./rest.crt --from-file=tls.key=./rest.key --from-file=ca.crt=./ca.crt -n <OPENSEARCH_NAMESPACE>`

    ### Admin Certificates
    `openssl req -out admin.csr -newkey rsa:2048 -nodes -keyout admin.key -subj "/CN=admin"`

    `openssl x509 -req -in admin.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out admin.crt -days 365 -sha256`

    `kubectl create secret generic admin-tls --from-file=tls.crt=./admin.crt --from-file=tls.key=./admin.key --from-file=ca.crt=./ca.crt -n <OPENSEARCH_NAMESPACE>`