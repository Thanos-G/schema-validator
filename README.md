# Schema Validator — Apex Arena Task

A technical interview challenge task built for the **Apex Arena** AI agent evaluation platform. The task tests an agent's ability to validate JSON data against a given schema, handle edge cases, and return structured results.

---

## 📋 Task Overview

The agent receives a JSON payload and a schema definition. It must:

- Parse and validate the input against the schema
- Identify and report any validation errors
- Return a structured response with the validation result

The grader evaluates the agent's output automatically and assigns a score between `0.0` and `1.0`.

---

## 📁 Repository Structure

```
schema-validator/
├── Dockerfile       # Container environment for the task
├── task.yaml        # Task definition and metadata
├── grader.py        # Automated grader (scores agent output)
└── README.md
```

> ⚠️ **Note:** The reference solution is not included in this repository.

---

## 🐳 Running Locally

### Prerequisites

- Docker Desktop (or Docker Engine on Linux)
- Python 3.10+

### Build the image

```bash
docker build -t schema-validator .
```

### Run the container

```bash
docker run --rm schema-validator
```

---

## 🧪 Grading

The grader (`grader.py`) evaluates the agent's output based on:

| Criterion | Description |
|---|---|
| Correctness | Valid/invalid classification matches expected result |
| Error reporting | Validation errors are identified accurately |
| Format | Output follows the required structure |

Scores are returned as a float in `[0.0, 1.0]`.

---

## 🛠️ Task Format

The task is defined in `task.yaml` and follows the Apex Arena task specification. It includes:

- Task ID and metadata
- Input/output format definitions
- Grading criteria and weights

---

## 📄 License

MIT License — feel free to use this as a template for your own Apex Arena tasks.
