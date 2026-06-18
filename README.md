# WebV Experiment

## Structure

`webv.md` is the bullet list of requirements for WebValidate - it was generated using Claude from <https://github.com/bartr/webvalidate>

`webv-prd.md` and `sessions.md` are generated from the docs directory

## Docs

`create-prd.mdc` and `prd-template.md` are used to go from `stream of conciousness md file` to PRD

`METHODOLOGY.md` is used on the PRD to plan 90-120 minute implementation sessions

## Modeling for LLM Code Generation

We explored formal modeling approaches including [Alloy](https://alloytools.org/),
[P](https://p-org.github.io/P/), and [TLA+](https://lamport.azurewebsites.net/tla/tla.html).
These tools are strong options for rigorous specification and verification, especially for complex state and concurrency behavior.

While powerful, they felt too complex to learn, and would have traded one kind of human complexity for another, less widely known complexity.

Our OpenAPI spike is intended to keep modeling understandable and practical for day-to-day development. We model lifecycle behavior using a custom `x-lifecycle` extension and generate Mermaid diagrams to keep the behavior easy to read and review.

This approach builds on OpenAPI as the de facto standard for describing services and schemas. The `x-*` extension mechanism is well-defined and widely used, which makes this path both flexible and familiar.
