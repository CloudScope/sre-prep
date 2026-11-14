# SRE Architecture Analysis: Synthetic Monitoring & Health Endpoint Design

**Document ID:** SRE-ARCH-2026-001  
**Target Service:** `payment-api` (Spring Boot 3.4.x / Java 21)  
**Baseline Setup:**
- Application Traffic (`server.port`): **`8080`** (`0.0.0.0`)
- Management Traffic (`management.server.port`): **`8081`**
- Management Binding (`management.server.address`): **`127.0.0.1`** (Strictly bound to loopback)
- **Sidecar Container Pattern**: A dedicated sidecar runs in the same Pod network namespace (`netns`) to access `127.0.0.1:8081`.

---

## 1. Executive Summary

When Spring Boot's Actuator is bound to **`127.0.0.1`**, the Linux kernel drops all packets not originating from within the local Pod. This delivers zero-trust host isolation: no external caller, Ingress, or neighboring Pod can reach port `8081` directly.

To perform synthetic monitoring under this constraint, SRE and security teams evaluate two distinct architectural approaches:
- **Condition 1**: Expose `/payment/api/v1/health` on application port `8080` (bound to `0.0.0.0`) requiring authorization. The sidecar focuses purely on metric collection over loopback.
- **Condition 2**: Keep Actuator unauthenticated on `127.0.0.1:8081`, and deploy a **Sidecar container** to bridge or execute synthetic monitoring for external/cluster observability systems.

---

## 2. Condition 1: Authenticated Application Endpoint (Port 8080) with Loopback Actuator

### 2.1 Architecture & Request Flow

```
+-----------------------------------+
| Synthetic Prober                  |
| (Splunk / Blackbox / Datadog)     |
+-----------------+-----------------+
                  | HTTP GET /payment/api/v1/health
                  | Header: Authorization: Bearer <SYNTHETIC_TOKEN>
                  v
+-------------------------------------------------------------+
| Kubernetes Ingress / API Gateway                            |
+-----------------------------+-------------------------------+
                              | Routes to Service port 8080
                              v
+---------------------------------------------------------------------------------------+
| payment-api Pod (Shared Network Namespace)                                            |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | Container 1: Spring Boot Application                                            |  |
|  |                                                                                 |  |
|  |  Port 8080 (0.0.0.0):                                                           |  |
|  |    1. Spring Security validates Bearer Token                                    |  |
|  |    2. Dispatches to PaymentHealthController                                     |  |
|  |    3. Queries internal HealthEndpoint bean in-process                           |  |
|  |    4. Returns 200 OK {"status": "UP"}                                           |  |
|  |                                                                                 |  |
|  |  Port 8081 (127.0.0.1):                                                         |  |
|  |    - Actuator bound strictly to loopback                                        |  |
|  +---------------------------------------^-----------------------------------------+  |
|                                          |                                            |
|                                          | Localhost scrape (127.0.0.1:8081)          |
|  +---------------------------------------+-----------------------------------------+  |
|  | Container 2: OpenTelemetry Sidecar                                              |  |
|  | - Scrapes metrics over loopback and pushes OTLP out to central collector        |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

### 2.2 Pros & Cons Analysis

#### Pros:
1. **Tests the Real Customer Path**:
   - Traverses DNS, Ingress, TLS, Service routing, Spring Boot dispatcher servlet, and Spring Security filters.
2. **Validates the Security Subsystem**:
   - Catches expired OAuth certs, revoked tokens, or broken security filter chain updates before customer traffic is broken.
3. **True Zero-Trust Actuator Isolation**:
   - Actuator is bound strictly to `127.0.0.1`. No external or cluster network interface exposes port `8081`.
4. **Simple Cluster Networking**:
   - Kubernetes `Service` only exposes one port: `8080`. No complex multi-port routing or NetworkPolicies needed.

#### Cons:
1. **Secret & Credential Lifecycle**:
   - Synthetic probers must store, rotate, and securely inject tokens (Bearer JWT or Basic Auth).
2. **Failure Blurring**:
   - A `401 Unauthorized` triggers a synthetic alert, which can be an expired token rather than an application runtime outage.
3. **In-Process Health Delegation Required**:
   - Requires custom controller code to bridge incoming requests to Spring Boot's internal `HealthEndpoint`.

### 2.3 Implementation Details (Condition 1)

#### A. Spring Boot Configuration (`application.yml`)
```yaml
server:
  port: 8080
  address: 0.0.0.0

management:
  server:
    port: 8081
    address: 127.0.0.1 # Strictly loopback
  endpoints:
    web:
      exposure:
        include: health,prometheus
```

#### B. Controller & Security (`PaymentHealthController.java` & `SecurityConfig.java`)
```java
@RestController
@RequestMapping("/payment/api/v1")
public class PaymentHealthController {
    private final HealthEndpoint healthEndpoint;

    public PaymentHealthController(HealthEndpoint healthEndpoint) {
        this.healthEndpoint = healthEndpoint;
    }

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getHealth() {
        HealthComponent health = healthEndpoint.health();
        boolean isUp = Status.UP.equals(health.getStatus());
        return ResponseEntity
            .status(isUp ? HttpStatus.OK : HttpStatus.SERVICE_UNAVAILABLE)
            .body(Map.of("status", health.getStatus().getCode(), "service", "payment-api"));
    }
}
```

```java
@Bean
public SecurityFilterChain applicationSecurityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(AbstractHttpConfigurer::disable)
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/payment/api/v1/health").hasRole("SYNTHETIC_PROBER")
            .anyRequest().authenticated()
        )
        .httpBasic(Customizer.withDefaults());
    return http.build();
}
```

---

## 3. Condition 2: Actuator on 127.0.0.1 (No Auth) with Sidecar Access

Because Actuator is bound to `127.0.0.1:8081`, an external synthetic prober (Splunk, Datadog, Prometheus Blackbox Exporter) **cannot establish a TCP connection across the pod boundary**.

To make this unauthenticated endpoint monitorable, the **Sidecar** must act as the intermediary using one of two patterns:

---

### Pattern 2A: Sidecar as an In-Pod Synthetic Prober (Push Model - Recommended)

The sidecar container executes synthetic probes locally across `127.0.0.1` and pushes the health result out to the monitoring system. No additional inbound ports are opened.

```
+---------------------------------------------------------------------------------------+
| payment-api Pod (Shared Network Namespace)                                            |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | Container 1: Spring Boot Application                                            |  |
|  |  - Port 8080 (0.0.0.0): Strict business traffic only                             |  |
|  |  - Port 8081 (127.0.0.1): Actuator (No Auth)                                    |  |
|  +---------------------------------------^-----------------------------------------+  |
|                                          |                                            |
|                                          | Periodic GET http://127.0.0.1:8081/actuator/health
|  +---------------------------------------+-----------------------------------------+  |
|  | Container 2: Synthetic Prober / OTel Sidecar                                    |  |
|  | - Evaluates HTTP 200 & {"status": "UP"}                                         |  |
|  | - Emits gauge metric: synthetic_probe_success{service="payment-api"} = 1        |  |
|  +---------------------------------------+-----------------------------------------+  |
+------------------------------------------|--------------------------------------------+
                                           | OTLP Push over gRPC (Cluster Internal)
                                           v
+---------------------------------------------------------------------------------------+
| Central Observability Gateway (OTel Collector / Prometheus / Splunk APM)              |
| Alert fires if: synthetic_probe_success == 0 or absent_over_time(...)                 |
+---------------------------------------------------------------------------------------+
```

#### Pros of Pattern 2A:
- **Zero Inbound Port Exposure**: Not even the sidecar opens an inbound listening port.
- **Zero Credentials Needed**: Probes run locally on loopback; no API tokens or passwords required.
- **Decoupled from Auth Failures**: Alerts strictly on application runtime health.

#### Cons of Pattern 2A:
- **Does Not Test Ingress / Network Layer**: If Ingress or K8s Service breaks, this probe still reports `UP`.

---

### Pattern 2B: Sidecar as a Secure Reverse Proxy (Pull Model)

The sidecar container listens on an internal Pod port (e.g. `8443` or `8082`), terminates network traffic, and reverse-proxies directly to `http://127.0.0.1:8081/actuator/health`.

```
+-----------------------------------+
| External / Cluster Prober         |
| (Splunk Private Agent / Blackbox) |
+-----------------+-----------------+
                  | HTTP/HTTPS GET to Service Port 8082
                  v
+---------------------------------------------------------------------------------------+
| payment-api Pod (Shared Network Namespace)                                            |
|                                                                                       |
|  +---------------------------------------------------------------------------------+  |
|  | Container 2: Reverse-Proxy Sidecar (Envoy / kube-rbac-proxy / NGINX)           |  |
|  | - Listens on 0.0.0.0:8082 (Restricted by NetworkPolicy)                         |  |
|  | - Validates network source or client cert                                       |  |
|  | - Forwards request to 127.0.0.1:8081/actuator/health                            |  |
|  +---------------------------------------+-----------------------------------------+  |
|                                          | Proxy over loopback                        |
|                                          v                                            |
|  +---------------------------------------------------------------------------------+  |
|  | Container 1: Spring Boot Application                                            |  |
|  | - Port 8081 (127.0.0.1): Responds with {"status": "UP"} (No Auth required)      |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

#### Pros of Pattern 2B:
- **Native Blackbox / Splunk Pull Compatibility**: Works with standard HTTP GET synthetic probers.
- **Clean Separation of Concerns**: Spring Boot does zero authentication on port `8081`; the sidecar handles all network boundary security.

#### Cons of Pattern 2B:
- **Additional Container & Port**: Requires maintaining a proxy container and exposing port `8082` on the Kubernetes Pod.
- **Requires NetworkPolicy**: Must enforce a Kubernetes `NetworkPolicy` to ensure port `8082` is not reachable by unauthorized cluster workloads.

---

### 2.4 Implementation Details (Condition 2)

#### A. Spring Boot Configuration (`application.yml`)
```yaml
server:
  port: 8080
  address: 0.0.0.0

management:
  server:
    port: 8081
    address: 127.0.0.1 # Strictly loopback
  endpoints:
    web:
      exposure:
        include: health,prometheus
  endpoint:
    health:
      show-details: never # Prevent leaking internal details
      probes:
        enabled: true
```

#### B. Spring Security Configuration (`SecurityConfig.java`)
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    // Filter 1: Management port (8081) - Permit unauthenticated health probes on loopback
    @Bean
    @Order(1)
    public SecurityFilterChain actuatorSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher(EndpointRequest.toAnyEndpoint())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(EndpointRequest.to("health")).permitAll()
                .anyRequest().denyAll()
            )
            .csrf(AbstractHttpConfigurer::disable);
        return http.build();
    }

    // Filter 2: Application port (8080) - Strict auth for all caller requests
    @Bean
    @Order(2)
    public SecurityFilterChain applicationSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .anyRequest().authenticated()
            )
            .httpBasic(Customizer.withDefaults());
        return http.build();
    }
}
```

#### C. Kubernetes Pod Deployment with Sidecar (`k8s/deployment.yaml`)
Demonstrating the sidecar pattern where the sidecar accesses `127.0.0.1:8081` and Kubelet uses `exec` probes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: payment-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: payment-api
    spec:
      containers:
        # Container 1: Spring Boot Application
        - name: payment-api
          image: payment-api:0.1.0
          ports:
            - name: http
              containerPort: 8080 # ONLY port 8080 is exposed
          # Kubelet exec probe runs inside the pod netns to reach 127.0.0.1
          livenessProbe:
            exec:
              command:
                - /bin/sh
                - -c
                - "wget -qO- http://127.0.0.1:8081/actuator/health/liveness | grep -q 'UP' || exit 1"
            initialDelaySeconds: 15
            periodSeconds: 10

        # Container 2: Sidecar Prober / Proxy
        - name: synthetic-sidecar
          image: curlimages/curl:8.12.0
          command:
            - /bin/sh
            - -c
            - |
              while true; do
                STATUS=$(curl -s http://127.0.0.1:8081/actuator/health | grep -o '"status":"UP"')
                if [ -n "$STATUS" ]; then
                  echo "payment_synthetic_health 1" > /tmp/metrics
                else
                  echo "payment_synthetic_health 0" > /tmp/metrics
                fi
                sleep 10
              done
```

---

## 4. Critical SRE Failure Mode: The "False-Green Health Check" (Silent Outage)

A dangerous architectural risk arises when **changing the synthetic monitoring health port to `8081`**:  
> **Can port `8081` report `200 OK {"status":"UP"}` while the application on port `8080` is completely broken and unable to serve customer traffic?**

**Yes, absolutely.** This failure mode is known in SRE as the **"Silent Outage"** or **"False-Green Trap"**.

### 4.1 The Underlying Cause: Independent Web Servers & Thread Pools

In Spring Boot, setting `management.server.port: 8081` causes the runtime to instantiate **two separate embedded web servers (e.g. Tomcat connectors)**:
1. **Application Connector (`0.0.0.0:8080`)**: Dedicated worker thread pool (default 200 threads) executing customer business logic and the main Spring Security filter chain.
2. **Management Connector (`127.0.0.1:8081`)**: Dedicated, completely independent management thread pool handling Actuator endpoints with a separate, lightweight filter chain.

```
                       +-------------------------------------------------------------+
                       | Spring Boot JVM Process                                     |
                       |                                                             |
                       |   +-----------------------------------------------------+   |
Incoming User Traffic  |   | Server 1: Application Connector (Port 8080)         |   |
(Real Customers) =====>|   | - Thread Pool: 200 worker threads [ALL EXHAUSTED]   |   |
                       |   | - Spring Security Filters: [BLOCKED / FAILING]      |   |
                       |   | - Result: HTTP 504 Gateway Timeout / Deadlock       |   |
                       |   +-----------------------------------------------------+   |
                       |                                                             |
                       |   +-----------------------------------------------------+   |
Synthetic Monitoring   |   | Server 2: Management Connector (Port 8081)          |   |
(Probing Actuator) ===>|   | - Thread Pool: Separate dedicated threads [IDLE]    |   |
                       |   | - Security: PermitAll on loopback                   |   |
                       |   | - Result: HTTP 200 OK {"status": "UP"} (FALSE GREEN)|   |
                       |   +-----------------------------------------------------+   |
                       +-------------------------------------------------------------+
```

### 4.2 Production Scenarios Where Port 8080 Fails While 8081 Stays "UP"

1. **Tomcat Worker Thread Pool Exhaustion on Port 8080**:
   - High traffic, unindexed database queries, or a downstream dependency hang locks up all 200 threads on port `8080`.
   - Real customers experience timeouts or dropped connections.
   - Port `8081` runs on an **idle, isolated thread pool**. The synthetic probe receives an instantaneous `200 OK {"status":"UP"}`. No alert fires.
2. **Spring Security Filter Chain Collapse on Port 8080**:
   - An expired JWT signing key, an unreachable JWKS/OAuth identity provider, or a misconfigured security filter causes port `8080` to reject all callers with `401 Unauthorized` or `500 Internal Server Error`.
   - Port `8081` has its own `permitAll()` filter chain, completely oblivious to the auth failure on port `8080`.
3. **Ingress, Service, or TLS Routing Breakage**:
   - A bad Kubernetes Ingress rule, routing misconfiguration, or expired public TLS certificate prevents user traffic from ever reaching port `8080`.
   - The synthetic sidecar on loopback or internal cluster probe accesses port `8081` directly, bypassing the broken Ingress entirely.
4. **TCP Connection Backlog Queue Overflow on Port 8080**:
   - Under surge load or after a long GC pause, port `8080` drops TCP SYN packets (`connection refused`). Port `8081` experiences near-zero connection load and accepts probe connections cleanly.

### 4.3 SRE Mitigations

#### Mitigation A (Primary Recommendation): Use Condition 1 for Synthetic Monitoring
Synthetic monitoring must test what customers experience. Probing port `8080` with authentication ensures that thread pool exhaustion, security filter collapses, and Ingress routing failures are caught immediately.

#### Mitigation B (If Probing Port 8081): Implement a Main Server HealthIndicator
If architectural constraints require probing port `8081`, link Actuator's health calculation to port `8080`'s Tomcat connector status:

```java
package com.sreprep.payment.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.boot.web.embedded.tomcat.TomcatWebServer;
import org.springframework.boot.web.servlet.context.ServletWebServerApplicationContext;
import org.springframework.stereotype.Component;

@Component
public class MainServerHealthIndicator implements HealthIndicator {

    private final ServletWebServerApplicationContext context;

    public MainServerHealthIndicator(ServletWebServerApplicationContext context) {
        this.context = context;
    }

    @Override
    public Health health() {
        if (context.getWebServer() instanceof TomcatWebServer tomcatServer) {
            org.apache.catalina.connector.Connector connector = tomcatServer.getTomcat().getConnector();
            
            // If the application connector on port 8080 is unavailable or paused, mark Actuator DOWN
            if (connector == null || !connector.getState().isAvailable()) {
                return Health.down().withDetail("mainServerPort8080", "CONNECTOR_UNAVAILABLE").build();
            }
        }
        return Health.up().withDetail("mainServerPort8080", "RUNNING").build();
    }
}
```

---

## 5. Side-by-Side Comparison Matrix

| Evaluation Dimension | Condition 1 (Port 8080 with Auth) | Condition 2 (127.0.0.1 via Sidecar, No Auth) |
| :--- | :--- | :--- |
| **Actuator Host Isolation** | Bound to `127.0.0.1` | Bound to `127.0.0.1` |
| **Monitors End-to-End User Path** | **Yes** (Ingress + Spring Security + Routing) | **No** (Monitors local container runtime only) |
| **Detects Port 8080 Thread Starvation** | **Immediate** (Probe times out) | **Blind** (Port 8081 responds on separate thread pool) |
| **Detects Spring Security Failures** | **Immediate** (Auth failure triggers alert) | **Blind** (Actuator uses separate filter chain) |
| **Credential & Secret Management** | **Required** (Synthetic prober needs auth token) | **Zero** (No credentials required) |
| **False Positive on Credential Expiry** | **Possible** (Expired token triggers synthetic alert) | **None** (Tests application health directly) |
| **Pod Inbound Port Attack Surface** | Port `8080` only | Port `8080` only (Push sidecar) or `8080` + `8082` (Proxy sidecar) |
| **Implementation Complexity** | Medium (Requires custom controller delegation) | Medium (Requires multi-container Pod manifest) |

---

## 6. Architectural Recommendation (SRE Verdict)

### The Production Standard: Dual-Tier Monitoring

When running Spring Boot with `management.server.address: 127.0.0.1`, high-reliability platforms adopt a **dual-tier monitoring strategy**:

1. **Tier 1 — Synthetic User Journey Monitoring (Condition 1)**:
   - Run external synthetic probes (Splunk Synthetics / Datadog / Prometheus Blackbox) targeting `https://api.yourdomain.com/payment/api/v1/health` on port `8080` with credentials.
   - **SRE Value**: Proves that external customers can successfully authenticate and execute requests across the entire infrastructure stack.

2. **Tier 2 — Infrastructure & Container Health (Condition 2 via Sidecar)**:
   - Keep Actuator on `127.0.0.1:8081` unauthenticated.
   - Use the **Sidecar** to scrape `/actuator/prometheus` and push metrics upstream via OTLP.
   - Use Kubernetes **`exec` probes** against `127.0.0.1:8081/actuator/health` so Kubelet can restart unresponsive containers without exposing any operational ports to the network.
