# Example: Incident Postmortem Input
# Feed this to: cat examples/inputs/postmortem-example.md | greybeard analyze --pack incident-postmortem

# Postmortem: API Outage — 2024-03-15

## Duration
14:32 UTC – 16:47 UTC (2h 15m)

## Impact
- 100% of API requests returning 500
- All users unable to access the application
- ~3,000 requests failed

## Timeline
- 14:28 — Deploy of v2.4.1 triggered by engineer
- 14:32 — Error rate spikes to 100%, alerts fire
- 14:35 — On-call engineer acknowledges alert
- 14:50 — Engineer begins investigating logs
- 15:20 — Root cause identified as missing env var
- 15:45 — Fix deployed
- 16:47 — Error rate returns to baseline, incident closed

## Root Cause
John forgot to add the new STRIPE_WEBHOOK_SECRET environment variable to the
production Railway environment before deploying. The application crashed on startup
because the variable was required but missing.

## Contributing Factors
- John was rushing to get the deploy out before end of day
- No pre-deploy checklist existed
- Alerts fired but were not acknowledged for 3 minutes

## Action Items
- [ ] John to be more careful with deployments going forward
- [ ] Maybe add a checklist somewhere
- [ ] Look into better alerting

## Lessons Learned
Human error caused this outage. Engineers need to be more diligent about following
deployment procedures and double-checking their work before shipping to production.
