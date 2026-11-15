# Module 3: Retrieval-Augmented Generation with ChromaDB

> Synthetic Sprints curriculum content created for this project.

## Why RAG
Language models do not know the Sprints curriculum and can hallucinate. Retrieval-augmented generation fetches relevant curriculum passages first and asks the model to answer only from them.

## The ingestion pipeline
1. Load documents from the curriculum folder.
2. Split them into chunks. The assignment requires chunks of at most 500 tokens and exactly 50 token positions of overlap between adjacent windows. The POC uses cl100k_base token offsets and verifies the reencoded text. Unicode boundaries may shorten a full window; unavailable exact tokenization fails explicitly.
3. Embed each chunk into a vector.
4. Store the vectors, the text and metadata such as the source file in ChromaDB.

## Chunk size trade-offs
Small chunks are precise but lose context. Large chunks keep context but dilute similarity scores and cost more tokens. Overlap protects against hard cuts. Measure retrieval quality on real questions before changing the settings.

## Retrieval
At query time the question is embedded, ChromaDB returns the top k nearest chunks using cosine distance, and the chunk text is placed in the prompt. Typical values are k between 3 and 5. The orchestrator requires retrieval to finish within 1000 milliseconds, so keep the collection local, warm the index at start-up and apply a timeout.

## Agentic RAG and self-reflection
Plain RAG retrieves once. Agentic RAG adds a reflection step: after retrieval the agent asks whether the context is sufficient to answer the question. If not, it reformulates the query, for instance by replacing everyday phrases with curriculum vocabulary, and searches again. Cap the number of attempts, and if the context is still insufficient say so honestly instead of guessing.

## Citing sources
Every answer should name the curriculum file it used so a learner or advisor can verify it.

## Evidence scope
The default embedder hashes terms deterministically. ChromaDB is real, but hosted embeddings and model reflection are not verified by offline runs. Reflection uses a deterministic coverage critique in offline mode. Cold first queries can exceed the 1000 ms target; warm-query benchmarks must be reported separately.
