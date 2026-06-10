# product-service

Scope: catalog + 10 product groups.

Current state: transitional wrapper. Runtime is mapped in `infrastructure/docker-compose.yml` to the existing Django codebase.

Next step: extract product/category/attributes/search modules from `store/` into this service.
