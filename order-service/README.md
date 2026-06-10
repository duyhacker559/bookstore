# order-service

Scope: order lifecycle + shipping orchestration.

Current state: transitional wrapper. Runtime is mapped in `infrastructure/docker-compose.yml` to the existing Django codebase.

Next step: extract order domain and keep payment/shipping integration via HTTP/events.
