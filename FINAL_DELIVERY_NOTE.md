# Final delivery note: 15 November 2026

**NOT READY for complete Sprints submission.** This new versioned package contains the available deliverables. The genuine 180-300 second recording is PENDING and the GitHub repository URL is MISSING. No paid inference, capture, remote publication or platform submission occurred during this preparation.

The authoritative technical deliverables are:

| File | SHA256 |
|---|---|
| [Technical report](submission/technical_report_current.pdf) | 5e15035b09f26132d93ea1ce375982ccd818be327910938606fcf79c3c0d1319 |
| [Ten-slide editable deck](submission/stakeholder_presentation_current.pptx) | c150a84859eade5f722d6bf2f6f5e028ca5a578f7213f8a67abde1530528023e |
| [Presentation PDF](submission/stakeholder_presentation_current.pdf) | f582b52a7657657179b4aad8f29d2ece208485f8679dc531e46c5f0603301118 |

Their technical content was checked against actual evidence and retained byte-for-byte. This note supersedes only the technical report pages 12 and 16 concerning old ZIP packaging: a new versioned ZIP is now intentionally prepared with an honest incomplete-deliverable manifest. The PDF/deck and older audit documents retain their dated scope. The earlier report/deck files remain available for provenance. Existing archives stay unchanged locally and are not nested into this release; the original-source baseline ZIP remains as evidence.

The internal PACKAGE_MANIFEST.json identifies every payload file and its SHA256, excluding the manifest itself. The separate sprints-delivery-TIMESTAMP.json receipt records the final ZIP hash, extraction, CRC, scan, size and extracted import checks. That receipt is external to avoid circular hashes. A clean publish folder under .build contains exactly the packaged project. No Git repository or remote is created automatically.

Preserved evidence: 157 full-suite tests passed, zero failures/skips; 70 focused startup/model tests passed, exit 0. These overlap and must not be added into a new total. No expensive sandbox suite, dependency installation or Docker rebuild was repeated for packaging. New validation uses a credential-free offline child environment, separate SQLite/Chroma paths and the existing audit interpreter. Execution from extracted/copied source is distinguished from an unperformed fresh dependency installation.

The user reports successful interactive APPROVE and REJECT runs. Separate preserved interactive receipts were not located. Existing scenarios named fixture and their approved_by_human/rejected_by_human status values prove automated mock-reviewer application transitions only. No new human decision is made by this packaging process. A genuine recording must show the human typing both decisions on separate proposals.

Language reasoning, reflection and judging remain heuristic/scripted; hashing embeddings are local. LangGraph, ChromaDB, SQLite and Linux Docker execution are real. The verified notebook has four executed code cells, zero errors, and labels injected grader faults. The normal demo leaves Fawry pending. Supplied learner data is included as requested and must remain private pending publication authorization; partner openings and curriculum are synthetic POC content.

Cold first retrieval remains PARTIAL: p95 1591.568 ms, n=20, 85% below 1000 ms. Prepared-first p95 13.129 ms (n=20) and warm p95 16.128 ms (n=200) do not establish a cold-query speedup. The 80% waiting-time reduction remains an unmeasured target. Live OpenAI inference and LLM-as-Judge behavior remain unexecuted. Existing provider/model/pricing plans are historical preparation and require a fresh official preflight plus explicit authorization before any future paid run.

Remaining delivery actions: [record and inspect the actual walkthrough](docs/demo_recording_script.md), obtain authorization for [private GitHub publication](docs/github_preparation.md), record the real URL, and create a new versioned ZIP after those additions. Live-inference and cold-retrieval acceptance gaps remain explicit for the assessor. Original kickoff media and production identity/durable storage remain unavailable. No mentor approval or official grade is claimed.

Use [reproduction instructions](docs/reproduce_submission.md). Do not execute the legacy fixed-name package script. Use scripts/finalize_delivery.py for new local delivery versions; a passing packaging receipt does not turn missing deliverables into completed requirements.
