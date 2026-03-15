# Internal Developer Platform Readiness Pack

Platform engineer or DevEx lead perspective — vendor-neutral and focused on platform maturity thinking.

## Quick Start

```bash
# Evaluate if a change is ready for platform automation
cat proposal.md | greybeard analyze --pack idp-readiness

# Learn the IDP maturity curve: docs → process → automation → self-service
cat proposal.md | greybeard analyze --pack idp-readiness --mode mentor
```

## Focus Areas

- **Maturity Curve**: Documentation first, then process, then automation
- **Developer Pain**: Is this driven by real developer need or platform team assumption?
- **Complexity Fit**: Is the complexity proportional to the problem scale?
- **Vendor Lock-in**: Are we avoiding unnecessary dependencies?

## When to Use This Pack

Use this pack when building platform infrastructure, internal tools, or considering automation. Helps evaluate whether you're automating the right thing at the right time.

---

_Created as part of the Greybeard community packs initiative._
