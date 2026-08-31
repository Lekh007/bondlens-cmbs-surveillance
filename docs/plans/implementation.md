# BondLens implementation guide

This document records the verification-oriented build sequence for the standalone
BondLens repository. Exact setup commands and current test commands live in the root
README.

## Tasks 1–14: backend and data workflow

- Define typed CMBS domain objects and distinguish issuance from current fields.
- Build keyless SEC submission and ABS-EE adapters with deterministic fixtures.
- Normalize and persist deal, loan, property, and reporting-period data.
- Add deterministic surveillance analytics and provenance-bearing tool results.
- Build retrieval, model-gateway, LangGraph orchestration, citation verification,
  prompt-injection boundaries, and evaluation hooks.
- Expose the workflow through FastAPI and a Redis-backed ingestion worker.

## Task 15: analyst interface

Build the responsive React analyst workbench using the design tokens in
`frontend/tailwind.config.js`. The interface must show period context, units, source
links, data-quality limitations, and verification state rather than presenting model
text as unsupported fact.

## Task 16: acceptance and browser verification

Exercise the golden loan-level questions, unsupported-property-trend refusal,
citation resolution, and source navigation. Browser tests run against deterministic
fixture handlers so CI remains fast and reproducible; optional live checks are kept
separate.

## Task 17: release checks

Run backend tests, lint, static typing, frontend tests, production build, Docker
Compose validation, and a secret scan. Publish only after all default checks pass and
known limitations are disclosed in the README.
