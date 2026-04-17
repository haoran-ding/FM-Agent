from config import *
from .llm_client import _openrouter_client, _retry_create, _llm_call, _extract_tagged


def _generate_block_post_condition(block, pre_condition, knowledge, language):
    info_str = f"\nAdditional context:\n{knowledge}" if knowledge else ""
    messages = [
        {"role": "system", "content": (
            f"You are an expert in formal verification of {language} programs. "
            f"Given a {language} code block and its pre-condition, generate the post-condition "
            "that describes the program state after the code block finishes execution. "
            "Cover all execution paths including early returns, exceptions, and normal flow-through. "
            f"Apply {language}-specific semantics (ownership, lifetimes, error handling, etc.) as appropriate. "
            "Be precise and unambiguous. Express the post-condition in natural language and formal logic."
        )},
        {"role": "user", "content": (
            f"Programming language: {language}\n\n"
            f"Pre-condition:\n{pre_condition}\n\n"
            f"Code block:\n```{language.lower()}\n{block}\n```\n"
            f"{info_str}\n"
            "Generate the post-condition. Wrap it within [POST_START] and [POST_END]."
        )}
    ]
    return _llm_call(_openrouter_client, LLM_MODEL, messages, "POST_START", "POST_END")


_LANGUAGE_EXPERTISE = {
    "rust": (
        "You are an expert in logic, formal verification, and the Rust programming language. "
        "You have deep knowledge of Rust's type system, ownership model, borrow checker, "
        "pattern matching exhaustiveness, trait system, and standard library. "
        "You know all Rust editions (2015, 2018, 2021, 2024) and their differences. "
    ),
    "c": (
        "You are an expert in logic, formal verification, and C compilation standards. "
        "You have encyclopedic knowledge of every C standard revision (C89, C99, C11, C17, C23) "
        "and know exactly which keywords, types, and constructs each revision introduced. "
    ),
    "c++": (
        "You are an expert in logic, formal verification, and C++ standards. "
        "You have encyclopedic knowledge of every C++ standard revision (C++98, C++03, C++11, C++14, C++17, C++20, C++23) "
        "and know exactly which keywords, types, templates, concepts, and constructs each revision introduced. "
        "You understand RAII, exception safety guarantees, move semantics, and the C++ object model. "
    ),
    "python": (
        "You are an expert in logic, formal verification, and the Python programming language. "
        "You have deep knowledge of Python's type system, exception handling, "
        "standard library, and semantics across Python 3.x versions. "
    ),
    "java": (
        "You are an expert in logic, formal verification, and the Java programming language. "
        "You have deep knowledge of Java's type system, generics, exception handling (checked and unchecked), "
        "collections framework, concurrency utilities, and semantics across Java SE versions (8 through 21). "
        "You understand the JVM memory model, garbage collection, class loading, autoboxing, "
        "and the differences between primitives and wrapper types. "
    ),
    "go": (
        "You are an expert in logic, formal verification, and the Go programming language. "
        "You have deep knowledge of Go's type system, interfaces, goroutines, channels, "
        "error handling conventions (multiple return values), defer/panic/recover, "
        "slices, maps, and semantics across Go versions (1.x through 1.22). "
        "You understand the Go memory model, garbage collection, and concurrency primitives. "
    ),
    "c#": (
        "You are an expert in logic, formal verification, and the C# programming language. "
        "You have deep knowledge of C#'s type system, generics, LINQ, async/await, "
        "nullable reference types, pattern matching, records, and semantics across C# versions (7.x through 12). "
        "You understand the .NET runtime, garbage collection, value types vs reference types, "
        "and the differences between struct and class. "
    ),
    "kotlin": (
        "You are an expert in logic, formal verification, and the Kotlin programming language. "
        "You have deep knowledge of Kotlin's null safety, extension functions, coroutines, "
        "sealed classes, data classes, delegation, and semantics across Kotlin versions (1.x through 2.x). "
        "You understand Kotlin's interop with Java, smart casts, and scope functions. "
    ),
    "swift": (
        "You are an expert in logic, formal verification, and the Swift programming language. "
        "You have deep knowledge of Swift's type system, optionals, protocol-oriented programming, "
        "generics, error handling (do/try/catch/throw), value semantics, ARC, "
        "and semantics across Swift versions (5.x through 6.x). "
    ),
    "php": (
        "You are an expert in logic, formal verification, and the PHP programming language. "
        "You have deep knowledge of PHP's type system, type juggling, traits, "
        "exception handling, generators, and semantics across PHP versions (7.x through 8.x). "
        "You understand PHP's reference counting, copy-on-write, and the differences between == and ===. "
    ),
    "ruby": (
        "You are an expert in logic, formal verification, and the Ruby programming language. "
        "You have deep knowledge of Ruby's dynamic type system, blocks/procs/lambdas, "
        "metaprogramming, mixins, exception handling (begin/rescue/ensure), "
        "and semantics across Ruby versions (2.x through 3.x). "
    ),
    "scala": (
        "You are an expert in logic, formal verification, and the Scala programming language. "
        "You have deep knowledge of Scala's type system, pattern matching, implicits/given, "
        "traits, case classes, higher-kinded types, and semantics across Scala 2.x and Scala 3. "
        "You understand the JVM runtime model and Scala's interop with Java. "
    ),
    "dart": (
        "You are an expert in logic, formal verification, and the Dart programming language. "
        "You have deep knowledge of Dart's sound null safety, type system, generics, "
        "async/await, streams, isolates, extension methods, and semantics across Dart versions (2.x through 3.x). "
    ),
    "cuda": (
        "You are an expert in logic, formal verification, CUDA programming, and C/C++ standards. "
        "You have deep knowledge of CUDA execution model, kernel launch semantics, "
        "memory hierarchy (global, shared, local, constant), thread synchronization, "
        "and GPU-specific concerns like race conditions and warp divergence. "
    ),
    "javascript": (
        "You are an expert in logic, formal verification, and the JavaScript programming language. "
        "You have deep knowledge of JavaScript's type coercion, prototypal inheritance, closures, "
        "event loop, async/await, Promises, and semantics across ECMAScript editions (ES5, ES6/ES2015 through ES2024). "
    ),
    "typescript": (
        "You are an expert in logic, formal verification, and the TypeScript programming language. "
        "You have deep knowledge of TypeScript's structural type system, generics, union/intersection types, "
        "type narrowing, type guards, utility types, declaration merging, and module resolution. "
        "You understand the full JavaScript runtime semantics and how TypeScript's compile-time checks "
        "interact with runtime behavior across TypeScript versions (2.x through 5.x). "
    ),
    "arkts": (
        "You are an expert in logic, formal verification, and the ArkTS programming language for OpenHarmony. "
        "You have deep knowledge of ArkTS's strict typing enforced at compile time, its declarative UI paradigm "
        "with struct-based components (@Component, @Entry), state management decorators (@State, @Prop, @Link, "
        "@Provide, @Consume, @StorageLink), and its restrictions compared to standard TypeScript "
        "(no structural typing, no any/unknown, no duck typing, limited union types, mandatory explicit types). "
        "You understand the ArkUI framework, the OpenHarmony application lifecycle, and the differences "
        "between ArkTS and TypeScript semantics. "
    ),
}


def _check_post_implies_spec(block, post_condition, spec_post_condition, knowledge, language):
    info_str = f"\nAdditional context:\n{knowledge}" if knowledge else ""
    lang_expertise = _LANGUAGE_EXPERTISE.get(language.lower(), f"You are an expert in logic, formal verification, and {language} programming. ")
    messages = [
        {"role": "system", "content": (
            lang_expertise +
            "Given a code block, its post-condition A (what the code actually does), and a specification post-condition B (what the code should do), "
            "determine whether there exists a concrete valid input where the code's behavior (A) violates the specification (B). "
            "Focus on finding CONCRETE COUNTEREXAMPLES: specific input values where the code produces an output that does not satisfy the specification. "
            "Check these common violation patterns:\n"
            "  1. The code rejects/filters out inputs that the specification says should be accepted (missing cases). "
            "Enumerate all required cases from the specification and the relevant language standard, and check each one against what the code handles.\n"
            "  2. The code accepts inputs that the specification says should be rejected.\n"
            "  3. The code produces a wrong output value for a valid input.\n"
            "For each potential violation, construct a specific input, trace what the code does (A), and check if the specification (B) is satisfied.\n"
            "If a violation exists, answer 'Yes' with a concrete counterexample. If no violation exists, answer 'No'.\n"
            "Wrap 'Yes' or 'No' with reasoning within [CHECK_START] and [CHECK_END]. "
            "If there is a violation, also wrap the offending statements within [STMT_START] and [STMT_END] "
            "(preserve the 'Line N:' prefix from the code block so the line number in the original file is visible), "
            "and the explanation within [REASON_START] and [REASON_END]."
        )},
        {"role": "user", "content": (
            f"Programming language: {language}\n\n"
            f"Code block:\n```{language.lower()}\n{block}\n```\n\n"
            f"Condition A (what the code actually does):\n{post_condition}\n\n"
            f"Condition B (what the specification requires):\n{spec_post_condition}\n"
            f"{info_str}\n"
            "Is there a concrete valid input where the code's behavior violates the specification? "
            "Enumerate all cases required by condition B and check if condition A covers each one. "
            "Provide a specific counterexample if any case is missing."
        )}
    ]
    for _ in range(MAX_SPC_ITER):
        response = _retry_create(_openrouter_client, LLM_MODEL, messages)
        check = _extract_tagged(response, "CHECK_START", "CHECK_END")
        if check:
            if "yes" in check.lower():
                stmts = _extract_tagged(response, "STMT_START", "STMT_END") or "(unable to extract)"
                reason = _extract_tagged(response, "REASON_START", "REASON_END") or check
                return False, stmts, post_condition, reason
            else:
                return True, None, None, None
        messages = messages + [
            {"role": "assistant", "content": response},
            {"role": "user", "content": "Please format your answer with [CHECK_START] and [CHECK_END] tags."}
        ]
    return True, None, None, None
