import json
import re
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Grader imports

from apex_arena._types import GradingResult



# Validation engine (mirrors solution.sh exactly)

def make_error(path: str, message: str, constraint: str, expected: str, actual: str) -> Dict:
    return {
        "path": path,
        "message": message,
        "constraint": constraint,
        "expected": str(expected),
        "actual": str(actual)
    }


def python_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def check_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    elif expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    elif expected == "boolean":
        return isinstance(value, bool)
    elif expected == "null":
        return value is None
    elif expected == "array":
        return isinstance(value, list)
    elif expected == "object":
        return isinstance(value, dict)
    return True


def check_format(value: str, fmt: str) -> Tuple[bool, str]:
    if fmt == "email":
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
            return False, "Invalid email format"
    elif fmt == "date":
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return False, "Invalid date format, expected YYYY-MM-DD"
    elif fmt == "uuid":
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value):
            return False, "Invalid UUID format"
    elif fmt == "uri":
        if not re.match(r'^https?://', value):
            return False, "Invalid URI format, must start with http:// or https://"
    return True, ""


def validate_string(value: str, schema: Dict, path: str) -> List[Dict]:
    errors = []
    if "minLength" in schema:
        n = schema["minLength"]
        if len(value) < n:
            errors.append(make_error(path, f"String length {len(value)} is less than minLength {n}", "minLength", f">= {n}", str(len(value))))
    if "maxLength" in schema:
        n = schema["maxLength"]
        if len(value) > n:
            errors.append(make_error(path, f"String length {len(value)} exceeds maxLength {n}", "maxLength", f"<= {n}", str(len(value))))
    if "pattern" in schema:
        pattern = schema["pattern"]
        if not re.search(pattern, value):
            errors.append(make_error(path, f"String does not match pattern '{pattern}'", "pattern", f"matches /{pattern}/", value))
    if "format" in schema:
        ok, msg = check_format(value, schema["format"])
        if not ok:
            errors.append(make_error(path, msg, "format", schema["format"], value))
    return errors


def validate_number(value, schema: Dict, path: str) -> List[Dict]:
    errors = []
    exclusive_min = schema.get("exclusiveMinimum", False)
    exclusive_max = schema.get("exclusiveMaximum", False)

    if "minimum" in schema:
        minimum = schema["minimum"]
        if exclusive_min:
            if not (value > minimum):
                errors.append(make_error(path, f"Value {value} must be greater than {minimum} (exclusiveMinimum)", "exclusiveMinimum", f"> {minimum}", str(value)))
        else:
            if value < minimum:
                errors.append(make_error(path, f"Value {value} is less than minimum {minimum}", "minimum", f">= {minimum}", str(value)))

    if "maximum" in schema:
        maximum = schema["maximum"]
        if exclusive_max:
            if not (value < maximum):
                errors.append(make_error(path, f"Value {value} must be less than {maximum} (exclusiveMaximum)", "exclusiveMaximum", f"< {maximum}", str(value)))
        else:
            if value > maximum:
                errors.append(make_error(path, f"Value {value} exceeds maximum {maximum}", "maximum", f"<= {maximum}", str(value)))

    if "multipleOf" in schema:
        multiple = schema["multipleOf"]
        if multiple != 0:
            remainder = value % multiple
            if not (math.isclose(remainder, 0, abs_tol=1e-9) or math.isclose(remainder, multiple, abs_tol=1e-9)):
                errors.append(make_error(path, f"Value {value} is not a multiple of {multiple}", "multipleOf", f"multiple of {multiple}", str(value)))

    return errors


def validate_array(value: list, schema: Dict, path: str, schemas_by_id: Dict) -> List[Dict]:
    errors = []
    if "minItems" in schema:
        n = schema["minItems"]
        if len(value) < n:
            errors.append(make_error(path, f"Array has {len(value)} items, minimum is {n}", "minItems", f">= {n}", str(len(value))))
    if "maxItems" in schema:
        n = schema["maxItems"]
        if len(value) > n:
            errors.append(make_error(path, f"Array has {len(value)} items, maximum is {n}", "maxItems", f"<= {n}", str(len(value))))
    if schema.get("uniqueItems", False):
        seen = []
        has_duplicates = False
        for item in value:
            serialized = json.dumps(item, sort_keys=True)
            if serialized in seen:
                has_duplicates = True
                break
            seen.append(serialized)
        if has_duplicates:
            errors.append(make_error(path, "Array items must be unique", "uniqueItems", "unique items", "duplicate items found"))
    if "items" in schema:
        item_schema = schema["items"]
        for i, item in enumerate(value):
            errors.extend(validate_value(item, item_schema, f"{path}[{i}]", schemas_by_id))
    return errors


def validate_object(value: dict, schema: Dict, path: str, schemas_by_id: Dict) -> List[Dict]:
    errors = []
    if "required" in schema:
        for key in schema["required"]:
            if key not in value:
                errors.append(make_error(f"{path}.{key}", f"Required property '{key}' is missing", "required", f"property '{key}' to exist", "property missing"))
    properties = schema.get("properties", {})
    for key, prop_schema in properties.items():
        if key in value:
            errors.extend(validate_value(value[key], prop_schema, f"{path}.{key}", schemas_by_id))
    if "additionalProperties" in schema and schema["additionalProperties"] is False:
        allowed = set(properties.keys())
        for key in value:
            if key not in allowed:
                errors.append(make_error(f"{path}.{key}", f"Additional property '{key}' is not allowed", "additionalProperties", "no additional properties", f"property '{key}' found"))
    return errors


def validate_value(value: Any, schema: Dict, path: str, schemas_by_id: Dict) -> List[Dict]:
    errors = []
    if not isinstance(schema, dict):
        return errors

    if "type" in schema:
        if not check_type(value, schema["type"]):
            errors.append(make_error(path, f"Expected type '{schema['type']}' but got '{python_type_name(value)}'", "type", schema["type"], python_type_name(value)))
            return errors

    if "enum" in schema:
        if value not in schema["enum"]:
            errors.append(make_error(path, f"Value must be one of {schema['enum']}", "enum", str(schema["enum"]), str(value)))

    if isinstance(value, str):
        errors.extend(validate_string(value, schema, path))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        errors.extend(validate_number(value, schema, path))
    if isinstance(value, list):
        errors.extend(validate_array(value, schema, path, schemas_by_id))
    if isinstance(value, dict):
        errors.extend(validate_object(value, schema, path, schemas_by_id))

    return errors


def compute_ground_truth(data: Dict) -> Dict:
    """Compute expected validation results from raw input data."""
    schemas_by_id = {(s.get("schema_id") or s.get("id")): s["schema"] for s in data.get("schemas", [])}

    validation_results = []
    errors_by_constraint: Dict[str, int] = {}
    total_errors = 0
    valid_count = 0
    invalid_count = 0

    for doc in data.get("documents", []):
        doc_id = doc.get("document_id") or doc.get("id")
        schema_id = doc["schema_id"]
        doc_data = doc["data"]

        if schema_id not in schemas_by_id:
            errors = [make_error("$", f"Schema '{schema_id}' is not defined", "schema_ref", f"schema with id '{schema_id}'", "schema not found")]
        else:
            errors = validate_value(doc_data, schemas_by_id[schema_id], "$", schemas_by_id)

        is_valid = len(errors) == 0
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
        total_errors += len(errors)
        for err in errors:
            c = err["constraint"]
            errors_by_constraint[c] = errors_by_constraint.get(c, 0) + 1

        validation_results.append({
            "document_id": doc_id,
            "schema_id": schema_id,
            "valid": is_valid,
            "errors": errors
        })

    return {
        "validation_results": validation_results,
        "summary": {
            "total_documents": valid_count + invalid_count,
            "valid_documents": valid_count,
            "invalid_documents": invalid_count,
            "total_errors": total_errors,
            "errors_by_constraint": errors_by_constraint
        }
    }


# Grading logic

def grade(_: str) -> "GradingResult":
# 1. Load ground-truth input (prefer /tests/ which agent cannot access)

    DATA_FILE_TESTS = Path("/tests/validation_request.json")
    DATA_FILE_WORKDIR = Path("/workdir/data/validation_request.json")

    raw_input = None
    for p in [DATA_FILE_TESTS, DATA_FILE_WORKDIR]:
        if p.exists():
            raw_input = p.read_text(encoding="utf-8")
            break

    if raw_input is None:
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback="ERROR: Input data file not found at /tests/ or /workdir/data/"
        )

    try:
        input_data = json.loads(raw_input)
    except json.JSONDecodeError as e:
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback=f"ERROR: Input data is not valid JSON: {e}"
        )

# 2. Compute expected results independently

    expected = compute_ground_truth(input_data)

# 3. Load agent output

    output_path = Path("/workdir/validation_results.json")
    if not output_path.exists():
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback="FAIL: Output file /workdir/validation_results.json was not created."
        )

    try:
        agent_output = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback=f"FAIL: Output file contains invalid JSON: {e}"
        )

# 4. Validate required top-level structure

    if "validation_results" not in agent_output:
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback="FAIL: Output is missing required field 'validation_results'."
        )
    if "summary" not in agent_output:
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback="FAIL: Output is missing required field 'summary'."
        )

# 5. Compare validation results document by document

    exp_results = expected["validation_results"]
    agent_results = agent_output["validation_results"]

    if len(agent_results) != len(exp_results):
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback=(
                f"FAIL: Expected {len(exp_results)} validation result(s), "
                f"got {len(agent_results)}."
            )
        )

    failures = []
    for i, (exp, got) in enumerate(zip(exp_results, agent_results)):
        doc_id = exp["document_id"]

        # Check document_id and schema_id
        if got.get("document_id") != exp["document_id"]:
            failures.append(f"doc #{i}: document_id mismatch (expected {exp['document_id']!r}, got {got.get('document_id')!r})")
        if got.get("schema_id") != exp["schema_id"]:
            failures.append(f"doc #{i}: schema_id mismatch (expected {exp['schema_id']!r}, got {got.get('schema_id')!r})")

        # Check valid flag
        if got.get("valid") != exp["valid"]:
            failures.append(
                f"{doc_id}: 'valid' should be {exp['valid']} but got {got.get('valid')}"
            )

        # Compare error count
        exp_errors = exp["errors"]
        got_errors = got.get("errors", [])
        if len(got_errors) != len(exp_errors):
            failures.append(
                f"{doc_id}: expected {len(exp_errors)} error(s), got {len(got_errors)}. "
                f"Expected constraints: {sorted(e['constraint'] for e in exp_errors)}, "
                f"got: {sorted(e['constraint'] for e in got_errors)}"
            )
            continue

        # Compare errors by constraint (order-insensitive)
        exp_constraints = sorted(e["constraint"] for e in exp_errors)
        got_constraints = sorted(e["constraint"] for e in got_errors)
        if exp_constraints != got_constraints:
            failures.append(
                f"{doc_id}: error constraint mismatch. "
                f"Expected {exp_constraints}, got {got_constraints}"
            )
            continue

        # Compare paths (order-insensitive)
        exp_paths = sorted(e["path"] for e in exp_errors)
        got_paths = sorted(e["path"] for e in got_errors)
        if exp_paths != got_paths:
            failures.append(
                f"{doc_id}: error path mismatch. "
                f"Expected paths {exp_paths}, got {got_paths}"
            )

# 6. Compare summary
    exp_summary = expected["summary"]
    got_summary = agent_output["summary"]

    for key in ["total_documents", "valid_documents", "invalid_documents", "total_errors"]:
        if got_summary.get(key) != exp_summary.get(key):
            failures.append(
                f"summary.{key}: expected {exp_summary.get(key)}, got {got_summary.get(key)}"
            )

    # errors_by_constraint
    exp_ebc = exp_summary.get("errors_by_constraint", {})
    got_ebc = got_summary.get("errors_by_constraint", {})
    if exp_ebc != got_ebc:
        failures.append(
            f"summary.errors_by_constraint mismatch.\n"
            f"  Expected: {exp_ebc}\n"
            f"  Got:      {got_ebc}"
        )

# 7. Return result
    if failures:
        feedback = "FAIL:\n" + "\n".join(f"  - {f}" for f in failures)
        return GradingResult(
            score=0.0,
            subscores={"validation": 0.0},
            weights={"validation": 1.0},
            feedback=feedback
        )

    total_docs = exp_summary["total_documents"]
    return GradingResult(
        score=1.0,
        subscores={"validation": 1.0},
        weights={"validation": 1.0},
        feedback=(
            f"PASS: All {total_docs} documents validated correctly. "
            f"Total errors detected: {exp_summary['total_errors']}."
        )
    )
    
