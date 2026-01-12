# Success Metrics

How to measure whether Cortex is achieving its goals.

## User Success Metrics

These indicate whether users are getting value from Cortex.

| Metric | Target | Why It Matters | How to Measure |
|--------|--------|----------------|----------------|
| Items captured per week | 10+ | Measures habit formation | Count items created |
| Search queries per week | 5+ | Proves retrieval value | Count search events |
| Chat sessions per week | 3+ | Shows AI is useful | Count chat conversations |
| 30-day retention | 40%+ | Real stickiness | Users active after 30 days |
| Items with connections | 60%+ | Knowledge graph working | Items with ≥1 connection |

### Interpreting User Metrics

**Low capture rate** (<5/week): Capture friction too high, or users don't see value yet.
- Check: Is the browser extension working? Is processing failing?

**Low search rate** (<2/week): Users aren't finding value in retrieval.
- Check: Is search quality good? Are users even trying it?

**Low chat usage** (<1/week): Chat isn't meeting expectations.
- Check: Is response quality acceptable? Are citations helpful?

**Low retention** (<30%): Users try it and leave.
- Check: Onboarding friction? Performance issues? Missing features?

## Technical Health Metrics

These indicate whether the system is performing well.

| Metric | Target | Why It Matters | How to Measure |
|--------|--------|----------------|----------------|
| Processing success rate | 95%+ | Pipeline reliability | Successful / total items |
| Search latency (p95) | <500ms | Feels instant | Time to results |
| Chat response time (p95) | <5s | Acceptable for local LLM | Time to first token |
| Embedding generation | <2s/chunk | Processing speed | Time per chunk |
| App crash rate | <1% | Stability | Crashes / sessions |
| Memory usage (idle) | <500MB | Resource efficiency | RAM when idle |
| Database size efficiency | <10KB/item | Storage reasonable | DB size / item count |

### Performance Budgets

**Startup time**: App should be usable within 3 seconds of launch.

**Search responsiveness**:
- Keystroke to results update: <100ms (debounced)
- Full search execution: <500ms for 10K items

**Chat responsiveness**:
- Time to first token: <2s (local), <1s (cloud)
- Full response: <10s for typical queries

**Processing throughput**:
- Webpage: <30s end-to-end
- PDF (10 pages): <60s end-to-end
- Bulk import (100 items): <30 minutes

### Degradation Thresholds

When metrics cross these thresholds, investigate immediately:

| Metric | Warning | Critical |
|--------|---------|----------|
| Processing success | <90% | <80% |
| Search latency p95 | >1s | >3s |
| Chat response p95 | >10s | >30s |
| Crash rate | >2% | >5% |
| Memory (idle) | >1GB | >2GB |

## Quality Metrics

These indicate whether AI features are working well.

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Search relevance | 80%+ relevant in top 5 | Manual evaluation |
| Chat groundedness | 90%+ answers cite sources | Check citations exist |
| Connection accuracy | 70%+ connections meaningful | Manual sampling |
| Extraction quality | 85%+ summaries accurate | Manual evaluation |

### Evaluating AI Quality

**Search relevance**: For a sample of queries, check if the top 5 results are actually relevant.
- Method: Weekly sample of 20 searches, manual review

**Chat groundedness**: Verify that answers are supported by cited sources.
- Method: Sample 10 chat responses, check each citation

**Connection accuracy**: Check if discovered connections make sense.
- Method: Sample 20 connections, evaluate if relationship is real

**Extraction quality**: Verify summaries and metadata are accurate.
- Method: Sample 10 items, compare extraction to source

## Business Metrics (If Monetized)

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Downloads | 10K in 6 months | Market validation |
| Paid conversions | 5%+ | Sustainable business |
| Refund rate | <5% | Product satisfaction |
| Support tickets per user | <0.5 | Product quality |

## Instrumentation

### What to Track (Locally)

All metrics are computed locally. No telemetry is sent.

```
Events to log:
- item_created { type, source, timestamp }
- item_processed { success, duration_ms, chunk_count }
- search_executed { query_length, result_count, duration_ms }
- chat_message { role, has_citations, duration_ms }
- connection_discovered { strength, type }
- app_started { version, platform }
- app_crashed { error_type } (if crash reporting enabled)
```

### Viewing Metrics

Users can view their own metrics in Settings > Statistics:
- Items saved this week/month
- Storage used
- Processing queue status
- AI provider usage (local vs cloud)

### Privacy Considerations

- All metrics stored locally only
- No network requests for analytics
- User can clear statistics anytime
- Crash reports are opt-in and anonymized
