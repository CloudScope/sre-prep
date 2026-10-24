# Error budget policy: orders-api

Applies to the SLOs in [`slo.md`](slo.md). Agreed by `<service owner>`, `<product owner>`, `<SRE lead>`. Review every quarter.

The point of this policy: the error budget is how product and engineering agree, in advance, on how to trade feature speed against reliability. When budget is left, ship. When it's gone, fix reliability first. Nobody has to argue it out during an incident.

## States and actions

| Budget remaining (30d) | State | What happens |
|---|---|---|
| > 50% | Healthy | Normal release cadence. Fine to use budget for experiments, chaos tests, risky migrations. |
| 25–50% | Caution | Releases continue. On-call reviews the top error sources weekly. Prefer smaller, reversible changes. |
| 0–25% | At risk | Only low-risk releases (bug fixes, config with fast rollback). At least one engineer on reliability work. |
| ≤ 0% (SLO missed) | Freeze | Feature releases stop until the budget recovers above 0% on the rolling window. Only reliability fixes and security patches ship. A postmortem is required. |

## Rules

1. **Single incident spending > 20% of budget** needs a postmortem with tracked action items, whatever the remaining budget.
2. **Exceptions** (for example a regulatory deadline during a freeze) need written sign-off from `<product owner>` and `<SRE lead>`, recorded in the postmortem or release ticket.
3. **Budget spent by dependencies** still counts. A freeze caused by a dependency is escalated to that team's owner, and the SLO doc is reviewed for whether the dependency needs its own SLO or graceful degradation.
4. **Planned maintenance** inside the SLO window spends budget like anything else. That is intentional: it's an honest record of what users experienced.
5. **If the SLO is consistently easy to meet** (budget > 90% left for a full quarter), tighten it or spend the budget on faster releases. If it's consistently missed while users are happy, the SLO is wrong. Fix the SLO, not the team.

## Escalation

| Trigger | Who is told | How |
|---|---|---|
| `SLOErrorBudgetBurnPage` | On-call | Page |
| `SLOErrorBudgetBurnTicket` | Owning team | Ticket in `<queue>` |
| Budget < 25% | Service owner, product owner | Weekly reliability review |
| Budget ≤ 0% | Service owner, product owner, SRE lead | Freeze announced in `<channel>` |
