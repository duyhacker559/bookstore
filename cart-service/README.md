# cart-service

Scope: cart and cart items.

Current state: transitional wrapper. Runtime is mapped in `infrastructure/docker-compose.yml` to the existing Django codebase.

Next step: extract `store.models.cart` and cart endpoints into dedicated service.
