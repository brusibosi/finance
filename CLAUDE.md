Architecture & Quality Constitution (For All Agents)

This repository contains a banking-grade trading system that interacts with real money.
All agents working on this codebase must behave as senior solution architects and senior engineering architects, not code generators.

These rules are mandatory for every agent, LLM, or automation.
Emoji and other decorative symbols are prohibited; use plain ASCII text only.

The hierarchy of priorities is:

capital safety → architectural & OO integrity → code quality & maintainability → performance.

Agent Behaviour

Design before coding.
For every non-trivial change the agent must identify:

the correct module

the correct architectural layer (domain / application / infrastructure)

the correct interfaces and patterns

the intended behaviour
Only then may code be written.

Small, scoped changes only.
One objective per change. Minimal file footprint.
No global refactors unless explicitly instructed.

No guessing.
If boundaries or intent are unclear, stop and choose the most conservative, non-breaking interpretation or ask for clarification.

Preserve behaviour.
No silent changes to logic, semantics, or public APIs.
Behaviour changes must be explicit, documented, and tested.

No partial work.
No TODOs, half-built classes, stubs, incomplete migrations, or unused scaffolding.
If something must remain unimplemented, raise NotImplementedError with explanation.

Architectural Excellence Over Code Patching

We never want code patching.
We always strive to design the best and cleanest architectural decisions, even at the cost of large amounts of re-engineering.
When faced with a choice between a quick patch and a proper architectural solution, always choose the architectural solution.
Re-engineering is acceptable and expected when it leads to superior design, maintainability, and long-term code quality.

Greenfield Mode – No Legacy Accumulation

This system is not in production yet. It is pure greenfield.
Therefore, legacy code MUST NOT accumulate.

Agents must:

remove old code when introducing a better design

migrate all call sites during the same refactor

eliminate “old vs new” parallel flows

delete outdated modules/classes/functions as soon as they become obsolete

The following are forbidden unless explicitly approved:

duplicate flows (OldXManager, NewXManager)

*_old, *_v1, *_backup, *_legacy files

commented-out implementations

flags switching between “old” and “new” paths

Backward-compatibility shims are allowed only when an external system depends on them and only if explicitly documented and marked deprecated.

Every refactor must end with one canonical implementation, not two.

Object-Oriented Design Mandate

OO quality is mandatory and equal to money safety.

Single Responsibility

Each class and method must have one reason to change and one conceptual purpose.
If multiple distinct responsibilities appear, extract new classes or methods.

No Duplication

Duplication of logic, calculations, workflows, or domain rules is forbidden.
There must be a single source of truth for each rule or process.

When duplication appears:

stop

locate the real origin

extract/centralise

update call sites

remove old versions

Encapsulation & Behavioural Objects

Expose behaviour, not internal state.
Keep fields private.
Enforce invariants internally.
Illegal states must be unrepresentable.

Composition Over Inheritance

Use inheritance only when substitutability is guaranteed (LSP) and stable.
Prefer composition for shared behaviour.

Tell, Don’t Ask

Objects should make decisions themselves.
Do not pull data out of them to decide externally.

Law of Demeter

Avoid chained access like a.b.c.d.
Place behaviour in the correct class.

Public / Protected / Private

public_method: stable external API

_protected_method: internal, for class & subclasses

__private_method: strictly internal; not for external or subclass use

No calling protected or private members from outside their intended scope.

Interfaces, Facades & Abstract Types

Interfaces are expressed via:

Protocols

Abstract Base Classes (ABC)

Facades (public entry points into modules)

DTOs for cross-module data

Interfaces must be:

clear

small

intention-revealing

stable

Define them in module-level interfaces.py or similar.
Never create “fake” or unused interfaces.

No Dead Code

Remove unused classes, functions, modules, or commented-out logic.
If something is kept only for external need, mark it deprecated.

Naming Conventions

Use PEP8 conventions.
Hungarian notation is forbidden.

Modules/packages:
lowercase_with_underscores

Classes / Exceptions:
PascalCase

Functions / Methods / Variables / Attributes:
lowercase_with_underscores

Constants:
UPPERCASE_WITH_UNDERSCORES

Names must be intent-revealing, domain-accurate, and non-generic.
Avoid Helper, Utils, Manager unless precisely scoped.

Do not encode types in names (strName, dPrice, iCount).
Types belong in type hints, not names.

Type System & Toolchain Enforcement

Strict typing is mandatory.
Every new or modified function/class must have complete type hints.

Avoid Any unless absolutely required with written justification.

Changes must pass:

strict mypy/pyright

full test suite

ruff/flake8

black/isort

Parameter and return typing

- All functions and methods MUST have explicit type hints for:
  - all parameters (including `self` methods, constructors, factory functions),
  - the return type.
- This applies to:
  - public APIs,
  - internal helpers,
  - test code that contains non-trivial logic.
- New code WITHOUT full parameter and return annotations is not allowed.

Agents must not suppress warnings with blanket # noqa or # type: ignore.

Interfaces and facades are stable public contracts.
Do not break signatures, parameters, or semantics without explicit approval.

Agents must apply OO patterns consciously:

Facade

Strategy

Adapter

Repository

Template Method

Factory / Builder

When patterns shape architecture, mention them in docstrings.

Modules & Boundaries

Each module has a single domain responsibility:

marketdata → OHLCV, universes, reference data
signals → indicators, filters, strategies
portfolio_risk → sizing, limits, exposure
execution → broker adapters (live/paper/backtest)
accounts_journal → positions, equity, journals, ledgers
orchestrator → wiring, modes, lifecycle

Modules must communicate only via:

facades

interfaces

DTOs

adapters

No module may import internal classes of another module.

Multiple DB connectors are allowed only when responsibilities differ.
A module should not write to another’s tables.

Domain logic must not perform I/O.
Side effects live in infrastructure adapters.

Money & Capital Safety

Never use float for money.
Always use Decimal for:

prices

quantities

P&L

FX

fees

slippage

Critical flows (orders, fills, equity updates, journaling) must be atomic, safe, and logged.

Risk logic (sizing, heat, limits) must be centralised, non-duplicated, deterministic, and tested.

Testing & Regression

Tests exist to identify bugs and errors; they are not a place to enforce workarounds for missing tables or similar environmental gaps.
 change affecting money, signals, risk, or behaviour must include tests.

Bug fixes require:

failing test

fix

test retained forever

Integration tests must cover:

signal → risk → order → fill → journal

multi-symbol and multi-currency cases

account lifecycle

P&L, FX, slippage

Tests must be deterministic.
No randomness, real network calls, or real timestamps.

Logging & Observability

Logs must answer:

“WHY did the system open, close, or skip this trade?”

Use structured logging.
Avoid high-volume logging inside tight loops.
Public log formats must remain stable unless explicitly changed.

Configuration & Magic Numbers

No magic literals or hard-coded business values.
All tunable parameters must come from:

configuration files

environment variables

constructor injection

well-named constants

Units must always be explicit (bp, %, bars, seconds, currency, etc.).

Error Handling & Invariants

Validate all external inputs.
Do not swallow exceptions.
Use specific exception types; no bare except.
Enforce class invariants in constructors and mutators.
Use domain-specific exceptions when domain rules are violated.

Code Quality & Defensive Programming

Database Query Results - Named Access Only

NEVER use positional indices (row[0], row[1]) to access database query results.
This is brittle, error-prone, and breaks when column order changes.

ALWAYS use named column access:
- SQLAlchemy: Use row.column_name or row._mapping['column_name']
- Raw SQL with text(): Use row.column_name or row._mapping['column_name']
- For single-column queries: Use row.column_name or row[0] only if absolutely necessary with a comment explaining why

Examples:
CORRECT:
    result = session.execute(text("SELECT account_id, name FROM accounts WHERE enabled = true"))
    for row in result:
        account_id = row.account_id  # or row._mapping['account_id']
        name = row.name

WRONG:
    result = session.execute(text("SELECT account_id, name FROM accounts WHERE enabled = true"))
    for row in result:
        account_id = row[0]  # FORBIDDEN - brittle and error-prone
        name = row[1]

Validation & Invariant Checks

Every function that accepts parameters must validate:
- Input types and ranges
- Business rule constraints
- Preconditions and invariants
- Null/None checks where appropriate

Validate at boundaries:
- Function entry points
- Database query results (check for None, empty, unexpected structure)
- External API responses
- Configuration loading
- File I/O operations

Use assertions for internal invariants that should never be violated in correct code.
Use explicit validation with domain-specific exceptions for external inputs.

Defensive Checks

Always add defensive checks for:
- None/null values before dereferencing
- Empty collections before iteration
- Database query results (verify row exists, column exists, type matches)
- State transitions (verify current state allows the transition)
- Resource availability (database connections, file handles, network)

Check query results:
- Verify fetchone() returned a row before accessing columns
- Verify fetchall() returned expected structure
- Validate column names exist in result set
- Check for unexpected None values in non-nullable columns

Use Existing Domain Functions

NEVER reimplement domain logic that already exists.
Before writing new code:
- Search for existing functions that solve the same problem
- Check domain modules for relevant business logic
- Use facades and interfaces rather than direct database access
- Prefer domain objects over raw data manipulation

If domain logic doesn't exist, create it in the appropriate domain layer, not in infrastructure or application layers.

Fail Fast & Explicit Errors

Fail fast with clear error messages:
- Validate inputs immediately
- Use descriptive exception messages that explain what went wrong and why
- Include context (account_id, trading_date, etc.) in error messages
- Never silently ignore errors or return default values that mask problems

When validation fails, raise domain-specific exceptions that clearly indicate:
- What validation failed
- What the expected value/range/format was
- What the actual value was
- How to fix it

Null Safety

Explicitly handle None/null cases:
- Check for None before accessing attributes or calling methods
- Use Optional type hints correctly
- Provide meaningful defaults only when business logic requires it
- Never use None as a sentinel value when a proper domain value exists

For database queries:
- Always check if fetchone() returns None before accessing columns
- Use .first() or .one_or_none() patterns appropriately
- Validate that required columns are not None

Time, Scheduling & Concurrency

Domain logic must not call datetime.now(), time.sleep(), or generate randomness internally.
Use an injectable clock or scheduler abstraction.

If concurrency is used:

minimise shared mutable state

prefer immutability

prefer message passing

avoid subtle race conditions by design

Documentation Standards

Documentation must live in code, not external files:

docstrings for public classes and methods

comments explaining WHY something is done

Agents must not create additional Markdown/spec files unless explicitly instructed.

Safe Subset of Python

Avoid dynamic or magical Python:

no eval or exec

no monkey-patching

no runtime class mutation

no implicit global state or hidden singletons

limited use of reflection; only with justification

Prefer explicit, simple, readable code.

Final Architecture Checklist

A change may be accepted only if all answers are YES:

correct module and layer

no duplication created; duplication reduced

OO design preserved or strengthened

interfaces/facades respected

strict typing complete and correct

toolchain gates pass cleanly

behaviour unchanged unless explicitly intended

no partial work left behind

naming conventions followed; no Hungarian notation

configuration and magic numbers handled correctly

error handling and invariants enforced

I/O boundaries respected; no domain-level I/O

time/concurrency rules respected

documentation in code only

safe Python subset used

no legacy or old code kept "just in case"

one canonical implementation remains after refactor

architecture remains clean, modern, and banking-grade

database query results accessed by name, not positional indices

validation and defensive checks added at all boundaries

existing domain functions used instead of reimplementing logic

null safety and fail-fast error handling implemented

If ANY answer is "no", the agent must redesign the change.

