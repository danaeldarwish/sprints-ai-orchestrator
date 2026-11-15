# Waiting-time measurement

The discovery working notes set an **80% reduction** target. No measured business baseline or post-deployment sample exists here; achieved improvement is **NOT VERIFIED**.

Define queue wait as service_start minus queue_entry. Define end-to-end learner lead time separately as final_completion minus initial_submission. Application latency and Chroma latency are software measurements; neither alone measures queue waiting.

Collect baseline and automation pilot events for the same activity mix (curriculum questions, grading, career matching), matched arrival schedules, operating hours, staffing and case complexity. Include human review wait, errors, retries, unresolved cases and rejected recommendations. Keep case IDs pseudonymous and store no code or salary in metric events.

For each cohort report n, completion rate, mean, median and p90 queue wait, mean and p90 lead time, and human-review fraction. Prefer paired cases or a documented matched cohort; state selection bias and sample limits. The 25 supplied learner records do not constitute 25 measured service events.

Reduction (%) = 100 * (baseline_mean_wait - pilot_mean_wait) / baseline_mean_wait. A zero baseline makes the percentage undefined. Save case-level timestamps and calculation code. For the 80% target, pilot mean wait must be at most 0.20 times the measured baseline using the same units and denominator.

Current baseline: unavailable. Current observed automation latency: reported separately in evidence/benchmark/rag_latency.json and evidence/commands; not a business wait-time improvement. Current evaluation sample for business waiting: 0. Proposed pilot size: at least 30 cases per activity per cohort, then reassess precision; this is a proposed sampling plan, not a statistical guarantee.
