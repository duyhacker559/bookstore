# user-service

Scope: staff, admin, customer.

Current state: transitional wrapper. Runtime is mapped in `infrastructure/docker-compose.yml` to the existing Django codebase.

Next step: extract auth/profile/staff/customer modules from `store/` into this service.
