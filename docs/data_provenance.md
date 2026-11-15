# Data provenance and privacy

- `data/sprints_learner_db.csv` contains 25 supplied rows. Its bytes remain unchanged from the original solution ZIP; evidence/baseline/archive_manifest.json records its hash.
- The claim that the kickoff mentions 500 learners comes from the user's initial independent findings and the old README. Original kickoff media are unavailable, so that source claim remains NOT VERIFIED. No additional learner records were synthesized.
- `data/sprints_learner.db` is a local SQLite materialization. The supplied database retains its original bytes. `build_database` reproducibly rebuilds 25 learner rows and 16 **synthetic** partner-opening rows from seed rules.
- Every opening has `is_synthetic=1`. Partner names appear for POC scenario matching; they are not verified current vacancies or partner commitments.
- All six curriculum Markdown documents are synthetic POC material. Security-related passages were corrected to match the current implementation. They are not official Sprints curriculum.
- The learner pass mark of 70, the 70/15/15 assessment rubric, salary bands, gross monthly salary convention, and Fawry-only tier policy are local assumptions unless explicitly supported by the working notes. The project submission pass score is 60 under the supplied project rubric.
- Matching uses the stored CSV Python score and modules. Automatic assessment does not write new grades to the learner database. Production needs a separately authorized grade-publishing workflow.
- The repository includes client learner data as explicitly requested. Keep this local package private until data-sharing authorization is established. No external sharing or publishing occurred during this audit.
