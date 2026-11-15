# Demo recording - PENDING

No screen-recording API or ffmpeg executable is available among the enabled tools. The available computer-use tool captures still screenshots. No video was fabricated or substituted with console text. There is no completed video and no verified video duration.

A recording should wait until the Linux sandbox integration succeeds; otherwise the required working secure-grading scene cannot be shown. Current offline demo honestly displays Unable to verify for both submissions.

## Exact 4 minute 15 second walkthrough

| Time | Actual on-screen action and narration |
|---|---|
| 0:00-0:25 | Open terminal in the project. Show README limitations. Say: This is an offline POC using real LangGraph, SQLite and Chroma; language reasoning is deterministic. |
| 0:25-0:45 | Run `python -m src.main sandbox-status`. Show a verified Linux image and controls. If unavailable, say unable to verify and do not claim secure grading works. |
| 0:45-1:25 | Run `python -m src.main demo --verbose`. Show curriculum sources and reflection/reformulation in metadata trace. Explain the curriculum is synthetic. |
| 1:25-2:10 | Show buggy then corrected clean_scores submissions and their real isolated test evidence. If unavailable, show the structured fallback and explain this is an open acceptance blocker. Do not replace this scene with the fixture notebook. |
| 2:10-2:40 | Show the SQLite career match with modules, stored score, EGP target and opening band. Explain openings are synthetic and matching uses actual local rows. |
| 2:40-3:25 | Run `python -m src.main review-demo` in a real terminal. Show the pending learner response. As authorized mock reviewer, explicitly type APPROVE and a rationale. Repeat and type REJECT; show the withheld response. |
| 3:25-3:50 | Run the named isolation/replay tests from the README. Explain mock identities and production identity limitations. |
| 3:50-4:15 | Show benchmark JSON and final audit matrix. State cold vs warm latency, paid OpenAI unverified, 80% waiting target unmeasured and remaining release gates. |

## Capture instructions

Use an available local recorder such as Windows Snipping Tool screen recording or OBS, set 1920x1080 or 1280x720, microphone narration, and capture only the terminal/report windows. Start capture before entering commands. Keep the actual application running; never edit fabricated scores or approval text into the recording. Save locally as `submission/demo_walkthrough.mp4`. A 4:15 runtime is the planned script duration, not an observed recording duration.

## Checklist

- Re-run the tests and sandbox integration immediately before capture.
- Keep all API keys, auth tokens, credential files and unrelated windows out of view.
- Narrate heuristic versus live inference and synthetic versus supplied data.
- Show pending before explicit review; show both terminal decisions.
- Include actual code execution only if verified containment is available.
- Inspect the whole video and verify audio legibility, actual 180-300 s duration, codec playback and file hash.
- Update the audit and manifest only after the real file exists. Until then: **PENDING**.
