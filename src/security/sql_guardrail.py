"""AST-Enforced Read-Only SQL Guardrail powered by sqlglot.
Guarantees zero database mutations, blocks multi-statement SQL injections,
and disallows unauthorized file system access or system functions.
"""

from __future__ import annotations

from typing import List, Set, Type
import sqlglot
from sqlglot import exp


class SecurityViolationError(Exception):
    """Raised when a generated SQL query violates read-only or safety constraints."""
    pass


class ReadOnlySQLGuardrail:
    """Enforces strict read-only execution by analyzing Abstract Syntax Trees (ASTs)."""

    # Prohibited SQL statement AST types (mutations and administrative DDL/DML)
    PROHIBITED_EXP_TYPES: Set[Type[exp.Expression]] = {
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Alter,
        exp.Create,
        exp.Command,
        exp.Pragma,
        exp.Set,
        exp.Transaction,
        exp.Commit,
        exp.Rollback,
        exp.Kill,
        exp.Merge,
        exp.TruncateTable,
        exp.Copy,
    }

    # Prohibited functions in DuckDB that could allow arbitrary filesystem access or external calls
    PROHIBITED_FUNCTIONS: Set[str] = {
        "read_csv",
        "read_csv_auto",
        "read_parquet",
        "read_json",
        "read_json_auto",
        "write_csv",
        "copy",
        "install",
        "load",
        "system",
        "getenv",
    }

    def __init__(self, dialect: str = "duckdb"):
        self.dialect = dialect

    def validate_and_sanitize(self, sql_query: str) -> str:
        """Parse, validate, and return sanitized read-only SQL query.

        Raises SecurityViolationError if the query violates any security policy.
        """
        if not sql_query or not sql_query.strip():
            raise SecurityViolationError("Empty SQL query provided.")

        clean_sql = sql_query.strip()
        # Remove trailing semicolon for parsing
        if clean_sql.endswith(";"):
            clean_sql = clean_sql[:-1].strip()

        # 1. Parse into AST statements
        try:
            statements = sqlglot.parse(clean_sql, read=self.dialect)
        except Exception as e:
            raise SecurityViolationError(f"SQL Syntax parsing failed: {e}")

        # 2. Block Multi-Statement Injection (e.g., "SELECT 1; DROP TABLE companies")
        if len(statements) != 1 or statements[0] is None:
            raise SecurityViolationError(
                f"Multi-statement execution prohibited. Detected {len(statements)} statements."
            )

        root = statements[0]

        # 3. Root Statement Must Be a Read-Only Query (Select or Union)
        if not isinstance(root, (exp.Select, exp.Union)):
            raise SecurityViolationError(
                f"Only read-only SELECT or UNION queries permitted. Root statement is: {type(root).__name__}"
            )

        # 4. AST Traversal: Check every child node for prohibited expression types
        prohibited_clean_names = {f.replace("_", "") for f in self.PROHIBITED_FUNCTIONS}

        for node in root.walk():
            # Check for prohibited expression classes
            for prohibited_type in self.PROHIBITED_EXP_TYPES:
                if isinstance(node, prohibited_type):
                    raise SecurityViolationError(
                        f"Prohibited SQL expression detected: {prohibited_type.__name__}"
                    )

            # Check node class name (e.g. ReadCSV, ReadParquet)
            class_name = type(node).__name__.lower()
            if class_name in prohibited_clean_names:
                raise SecurityViolationError(
                    f"Unauthorized filesystem or system function access prohibited: '{class_name}'"
                )

            # Check for dangerous system functions
            if isinstance(node, (exp.Anonymous, exp.Func)):
                func_name = getattr(node, "name", "").lower() or type(node).__name__.lower()
                if func_name in self.PROHIBITED_FUNCTIONS or func_name.replace("_", "") in prohibited_clean_names:
                    raise SecurityViolationError(
                        f"Unauthorized filesystem or system function access prohibited: '{func_name}'"
                    )

        # 5. Return standardized sanitized SQL string
        return root.sql(dialect=self.dialect)

    def is_safe(self, sql_query: str) -> bool:
        """Convenience method returning True if safe, False otherwise."""
        try:
            self.validate_and_sanitize(sql_query)
            return True
        except SecurityViolationError:
            return False
