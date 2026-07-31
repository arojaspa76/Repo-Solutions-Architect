# Sprint 0 — Decisions & Notes

## ADR-001: Cosmos DB Serverless for dev environment
**Date:** 2026-07  
**Status:** Accepted  
**Decision:** Use EnableServerless capability for the dev Cosmos DB account.  
**Rationale:** Zero cost when idle; dev workloads are intermittent.  
**Consequence:** Serverless cannot be combined with multi-region writes.
Switch to provisioned throughput (400 RU/s auto-scale) for staging/prod.

## ADR-002: Key Vault RBAC authorization model
**Date:** 2026-07  
**Status:** Accepted  
**Decision:** enableRbacAuthorization: true on Key Vault (no legacy access policies).  
**Rationale:** RBAC is the current Microsoft recommended approach; provides
audit trail via Azure Activity Log; integrates with PIM for just-in-time access.  
**Consequence:** All access must be granted via role assignments
(Key Vault Secrets Officer / User), not access policy entries.

## Sprint Notes

<!-- Add meeting notes, blockers, and decisions made during Sprint 0 here -->
