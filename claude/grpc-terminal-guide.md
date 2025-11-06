# gRPC Terminal - HTTP/2 Bidirectional Streaming

## Overview

This implementation provides true HTTP/2 bidirectional streaming for terminal I/O using gRPC. Unlike the SSE + HTTP POST approach, this uses a single bidirectional stream for both input and output.

## Architecture

```
┌─────────┐         ┌────────┐         ┌──────────┐
│ Browser │ ◄─────► │ Envoy  │ ◄─────► │ gRPC     │
│ Client  │         │ Proxy  │         │ Server   │
│(grpc-web)│        │        │         │(Python)  │
└─────────┘         └────────┘         └──────────┘
   HTTP/1.1           gRPC/HTTP2
   grpc-web
```

## Components

### 1. Backend (Python)

- **Protocol Buffer**: `backend/proto/terminal.proto`
- **gRPC Service**: `backend/grpc_server/terminal_service.py`
- **Server**: `backend/grpc_server/server.py`

### 2. Proxy (Envoy)

gRPC-Web requires a proxy to translate between HTTP/1.1 (browser) and HTTP/2 (gRPC server).

#### Install Envoy

**macOS:**
```bash
brew install envoy
```

**Linux:**
```bash
# Download from https://github.com/envoyproxy/envoy/releases
```

**Docker:**
```bash
docker pull envoyproxy/envoy:v1.28-latest
```

#### Envoy Configuration

Create `envoy.yaml`:
```yaml
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          codec_type: AUTO
          stat_prefix: ingress_http
          access_log:
          - name: envoy.access_loggers.stdout
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.access_loggers.stream.v3.StdoutAccessLog
          route_config:
            name: local_route
            virtual_hosts:
            - name: local_service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: grpc_service
                  timeout: 0s
                  max_stream_duration:
                    grpc_timeout_header_max: 0s
              cors:
                allow_origin_string_match:
                - prefix: "*"
                allow_methods: GET, PUT, DELETE, POST, OPTIONS
                allow_headers: keep-alive,user-agent,cache-control,content-type,content-transfer-encoding,x-accept-content-transfer-encoding,x-accept-response-streaming,x-user-agent,x-grpc-web,grpc-timeout
                max_age: "1728000"
                expose_headers: grpc-status,grpc-message
          http_filters:
          - name: envoy.filters.http.grpc_web
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.grpc_web.v3.GrpcWeb
          - name: envoy.filters.http.cors
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.cors.v3.Cors
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router

  clusters:
  - name: grpc_service
    connect_timeout: 0.25s
    type: LOGICAL_DNS
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options: {}
    load_assignment:
      cluster_name: grpc_service
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: 127.0.0.1
                port_value: 50051
```

#### Run Envoy

```bash
envoy -c envoy.yaml
```

### 3. Frontend (Browser)

#### Install Dependencies

```bash
cd web_client
npm install grpc-web google-protobuf
```

#### Generate JavaScript Code

```bash
protoc -I=../backend/proto terminal.proto \
  --js_out=import_style=commonjs:./src/proto \
  --grpc-web_out=import_style=commonjs,mode=grpcwebtext:./src/proto
```

#### Usage Example

```javascript
import {TerminalClient} from './proto/terminal_grpc_web_pb';
import {CreateSessionRequest, TerminalRequest, InputData} from './proto/terminal_pb';

// Create client pointing to Envoy proxy
const client = new TerminalClient('http://localhost:8080', null, null);

// Create session
const createReq = new CreateSessionRequest();
createReq.setRows(24);
createReq.setCols(80);
createReq.setCwd('/workspace');
createReq.setShell('bash');

client.createSession(createReq, {}, (err, response) => {
  if (err) {
    console.error(err);
    return;
  }

  const sessionId = response.getSessionId();

  // Start bidirectional stream
  const stream = client.stream({});

  // Handle incoming messages
  stream.on('data', (response) => {
    if (response.hasOutput()) {
      const output = response.getOutput();
      console.log('Output:', output.getData());
    } else if (response.hasExit()) {
      console.log('Exit code:', response.getExit().getExitCode());
      stream.cancel();
    } else if (response.hasError()) {
      console.error('Error:', response.getError().getMessage());
    }
  });

  stream.on('error', (err) => {
    console.error('Stream error:', err);
  });

  stream.on('end', () => {
    console.log('Stream ended');
  });

  // Send input
  const termReq = new TerminalRequest();
  termReq.setSessionId(sessionId);
  const inputData = new InputData();
  inputData.setData('ls -la\n');
  termReq.setInput(inputData);
  stream.write(termReq);
});
```

## Running

### 1. Start Backend with gRPC

```bash
export ENABLE_GRPC_SERVER=true
export GRPC_PORT=50051
uv run backend/server.py
```

### 2. Start Envoy Proxy

```bash
envoy -c envoy.yaml
```

### 3. Start Frontend

```bash
cd web_client
npm run dev
```

## Configuration

### Backend Environment Variables

- `ENABLE_GRPC_SERVER`: Set to `true` to enable gRPC server (default: `false`)
- `GRPC_PORT`: gRPC server port (default: `50051`)

### Frontend Environment Variables

- `VITE_GRPC_ENABLED`: Set to `true` to use gRPC instead of HTTP/SSE
- `VITE_GRPC_URL`: Envoy proxy URL (default: `http://localhost:8080`)

## Comparison

| Feature | HTTP Polling | SSE + POST | gRPC Bidirectional |
|---------|-------------|------------|-------------------|
| Output | Polling | Server Push | Server Push |
| Input | POST | POST | Client Push |
| Protocol | HTTP/1.1 | HTTP/1.1 | HTTP/2 |
| Efficiency | Low | Medium | High |
| Latency | High | Medium | Low |
| Browser Support | ✓ | ✓ | ✓ (via grpc-web) |
| Proxy Required | ✗ | ✗ | ✓ (Envoy) |

## Advantages

1. **True Duplex**: Single bidirectional stream for both input and output
2. **Lower Latency**: No polling, immediate push from both sides
3. **Efficient**: HTTP/2 multiplexing, header compression
4. **Type Safe**: Protocol Buffers ensure type safety
5. **Scalable**: Better resource utilization than polling

## Disadvantages

1. **Complexity**: Requires Envoy proxy for browser support
2. **Deployment**: Additional component to deploy and manage
3. **Debugging**: More difficult to debug than HTTP REST APIs

## Recommendation

- **Development**: Use SSE + POST (simpler, no proxy required)
- **Production with high load**: Use gRPC (better performance, scalability)
- **Simple deployments**: Use SSE + POST (fewer moving parts)
