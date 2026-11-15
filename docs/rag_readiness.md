# Application readiness and the 1000 ms retrieval criterion

The operational serving contract is **prepared retrieval**: learner requests start only after actual Chroma client/collection initialization, a real preparation query and graph construction succeed. src/startup.py returns READY with a service only after these steps. The CLI prints that status before its first learner request. A failed preparation returns UNAVAILABLE, accepting_learner_requests=false, no service, and CLI exit code2. It exposes exception class only, not private paths. A serving host must retain this gate; trusted warm=False overrides are for tests and benchmarks only.

The preparation query exercises Chroma's public query API to load the persisted collection/index as needed. It is not a claim that a private index-loading API or every possible shard has been preloaded. Readiness is a startup observation, not ongoing health monitoring. Later retrieval failures/timeouts still produce structured Unable to verify responses.

The 1000 ms operational interval starts at retrieve() entry and ends with source-bearing results, including local query embedding, executor dispatch and query work. It excludes process imports, initial collection/index preparation, LLM generation, database matching and human review wait. This is an operational interpretation for demonstration and must be agreed with the assessor; it does not amend the assignment or prove an unconditional sub-second guarantee. Until agreed, the general latency requirement remains PARTIAL.

Preserved measurements: unprepared cold n20 p95=1591.568ms, max1593.507ms,85% below1000; prepared first n20 p95=13.129ms,max36.962ms,100%; warm n200 p95=16.128ms,max65.852ms,100%. Startup preparation itself p95=1913.966ms,max3216.537ms; process start/query/exit p95=14760.504ms. All slow samples remain in evidence/followup_20261115/rag_latency.json. No cold-query speedup is claimed.

A fresh local startup verification is captured in evidence/demonstration_20261115/readiness_actual.stdout.txt and its command/exit receipt. Its elapsed time is one readiness observation, not a replacement benchmark. Focused tests check ordering, blocked graph exposure during preparation, clear failed startup and rejection of a serving warm=False override.

A running Chroma worker cannot be forcibly cancelled by the current thread-pool timeout. Readiness failure prevents service exposure, but hard process shutdown and sustained-load recovery need production supervision. Startup readiness does not certify ongoing health or concurrency capacity.
