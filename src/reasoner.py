import re
from config import *
from .prompts import _generate_block_post_condition, _check_post_implies_spec


def _split_into_blocks(func):
    lines = func.strip().split('\n')
    total = len(lines)
    if total <= GRANULARITY:
        return [func.strip()]

    blocks = []
    i = 0
    while i < total:
        remaining = total - i
        if remaining <= GRANULARITY * 2:
            blocks.append('\n'.join(lines[i:]))
            break
        end = i + GRANULARITY
        blocks.append('\n'.join(lines[i:end]))
        i = end
    return blocks


_TERMINATING_PATTERNS = {
    "rust": r'\b(return\b|panic!\s*\(|std::process::exit\s*\(|unreachable!\s*\()',
    "c": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|longjmp\s*\()',
    "c++": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|throw\s|std::terminate\s*\(|std::exit\s*\()',
    "python": r'\b(return\b|sys\.exit\s*\(|raise\s|exit\s*\(|quit\s*\()',
    "cuda": r'\b(return\b|exit\s*\(|_Exit\s*\(|abort\s*\(|__trap\s*\()',
    "java": r'\b(return\b|throw\s|System\.exit\s*\()',
    "go": r'\b(return\b|panic\s*\(|log\.Fatal\w*\s*\(|os\.Exit\s*\()',
    "c#": r'\b(return\b|throw\s|Environment\.Exit\s*\()',
    "kotlin": r'\b(return\b|throw\s|exitProcess\s*\(|System\.exit\s*\()',
    "swift": r'\b(return\b|throw\s|fatalError\s*\(|preconditionFailure\s*\(|exit\s*\()',
    "php": r'\b(return\b|throw\s|die\s*\(|exit\s*\()',
    "ruby": r'\b(return\b|raise\s|abort\s*\(|exit\s*\(|exit!\s*\()',
    "scala": r'\b(return\b|throw\s|sys\.exit\s*\(|System\.exit\s*\()',
    "dart": r'\b(return\b|throw\s|exit\s*\()',
    "javascript": r'\b(return\b|throw\s|process\.exit\s*\()',
    "typescript": r'\b(return\b|throw\s|process\.exit\s*\()',
    "arkts": r'\b(return\b|throw\s|process\.exit\s*\()',
}


def _has_terminating_statement(block, language):
    pattern = _TERMINATING_PATTERNS.get(language.lower())
    if not pattern:
        pattern = r'\b(return\b|exit\s*\(|raise\s|throw\s|abort\s*\()'
    return re.search(pattern, block) is not None


def _parse_spec_conditions(spec):
    pre_match = re.search(r'Pre-condition:\s*\n(.*?)(?=\nPost-condition:|\Z)', spec, re.DOTALL)
    post_match = re.search(r'Post-condition:\s*\n(.*)', spec, re.DOTALL)
    pre = pre_match.group(1).strip() if pre_match else None
    post = post_match.group(1).strip() if post_match else None
    return pre, post


def reasoner(func, spec, info, language):
    # Step 1: Parse pre-condition and post-condition directly from spec
    pre_condition, spec_post_condition = _parse_spec_conditions(spec)
    if not pre_condition or not spec_post_condition:
        return "Failed to parse pre/post conditions from the spec."

    # Step 2: Split function into code blocks (each >= GRANULARITY lines)
    blocks = _split_into_blocks(func)

    # Step 3: Process each block sequentially
    current_pre = pre_condition
    for i, block in enumerate(blocks):
        # Generate post-condition using Claude Sonnet 4.6
        post_condition = _generate_block_post_condition(block, current_pre, info, language)
        if not post_condition:
            return f"Failed to generate post-condition for block {i+1}."

        # Check against spec post-condition if block has terminating statements
        # or if this is the last block (implicit return at end of function)
        is_last_block = (i == len(blocks) - 1)
        if _has_terminating_statement(block, language) or is_last_block:
            passed, stmts, post_cond, reason = _check_post_implies_spec(
                block, post_condition, spec_post_condition, info, language
            )
            if not passed:
                return (
                    f"Verification FAILED.\n"
                    f"Statements triggering the violation:\n{stmts}\n\n"
                    f"Post-condition:\n{post_cond}\n\n"
                    f"Reason for violation:\n{reason}"
                )

        # Use current block's post-condition as next block's pre-condition
        current_pre = post_condition

    return "The function passes the verification. All code blocks satisfy the specification's post-condition."

def _sanitize_strings(obj):
    """Remove non-ASCII characters from all string values in a dict/list."""
    if isinstance(obj, str):
        return obj.encode("ascii", "ignore").decode("ascii")
    if isinstance(obj, dict):
        return {k: _sanitize_strings(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_strings(v) for v in obj]
    return obj
