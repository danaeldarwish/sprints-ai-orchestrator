# Module 1: Python Foundations and How Assignments Are Graded

> Synthetic Sprints curriculum content created for this project (the client supplied no curriculum files).

## Functions and return values
A Python function groups reusable logic. Define it with `def`, give it a clear name, and return a value instead of printing it whenever another part of the program needs the result. Every function in a Sprints assignment should have a docstring that states what it takes, what it returns, and what edge cases it handles.

## Handling messy data
Real learner data contains missing values (`None`) and invalid values (negative scores). Filter them out explicitly with a list comprehension, for example `valid = [s for s in scores if s is not None and s >= 0]`, and decide what to return when nothing valid remains. Averages of an empty list raise `ZeroDivisionError`, so guard that case first.

## Errors and exceptions
Use `try` and `except` with a specific exception type such as `ValueError`. A bare `except:` hides bugs and loses marks. Read tracebacks from the bottom up: the last line names the exception, and the line above shows where it happened.

## How Python assignments are graded
Every Python assignment is scored out of 100 with a fixed rubric:
- Correctness, 70 points: the share of hidden test cases the submission passes.
- Execution hygiene, 15 points: the code runs without a runtime error, timeout, or blocked operation.
- Readability, 15 points: a docstring (5), lines kept under 100 characters (5), and no bare `except` or wildcard imports (5).

The learner assessment pass mark is a local POC assumption of 70 out of 100, distinct from the project submission passing score of 60. Grading runs the submission in a restricted sandbox: only standard-library modules such as `math`, `statistics`, `itertools`, `collections`, `re` and `json` are allowed, and file access, networking and process creation are blocked. Each submission has a 5 second execution-time limit. Execution requires the verified restricted Linux container. When it is unavailable, no grade is issued; the response is Unable to verify. The container boundary remains unverified until its integration checks pass.

Feedback must be specific: name the failing test, show the expected and actual values, and say what to change. Generic comments such as "good job" are not accepted by reviewers.

## Practice assignments
Assignment `fizzbuzz` asks learners to print the numbers 1 to 15, replacing multiples of 3 with Fizz, multiples of 5 with Buzz, and multiples of both with FizzBuzz. Assignment `clean_scores` asks for a function that returns the average of the valid scores in a list, rounded to two decimals.
