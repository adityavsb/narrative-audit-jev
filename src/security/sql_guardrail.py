"""AST-Enforced Read-Only SQL Guardrail powered by sqlglot.
Restricts execution to read-only queries and blocks multi-statement SQL injections
against registered benchmark tables.
"""

from __future__ import annotations

from typing import List, Optional, Set, Type
import sqlglot
from sqlglot import exp


class SecurityViolationError(Exception):
    """Raised when a generated SQL query violates read-only or safety constraints."""
    pass


ALLOWED_TABLES: Set[str] = {
    "companies",
    "quarterly_financials",
    "segment_disclosures",
    "transcripts",
}


class ReadOnlySQLGuardrail:
    """Enforces strict read-only execution by analyzing Abstract Syntax Trees (ASTs) against an allowlist."""

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
        exp.CurrentVersion,
    }

    def __init__(self, dialect: str = "duckdb", allowed_tables: Optional[Set[str]] = None):
        self.dialect = dialect
        self.allowed_tables = {t.lower() for t in (allowed_tables or ALLOWED_TABLES)}

    def validate_and_sanitize(self, sql_query: str) -> str:
        """Parse, validate against allowlist, and return sanitized read-only SQL query."""
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

        # 4. Check for prohibited statement expression types
        for prohibited_type in self.PROHIBITED_EXP_TYPES:
            if root.find(prohibited_type):
                raise SecurityViolationError(
                    f"Prohibited SQL expression detected: {prohibited_type.__name__}"
                )

        # 5. Collect CTE names defined in query
        cte_names = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}

        # 6. Strict Table allowlist verification
        for table in root.find_all(exp.Table):
            if not isinstance(table.this, exp.Identifier):
                raise SecurityViolationError(
                    "Table functions, file paths, and subquery literals are prohibited in FROM."
                )
            if table.args.get("db") or table.args.get("catalog"):
                raise SecurityViolationError("Schema-qualified table names are prohibited.")
            t_name = table.name.lower()
            if t_name not in self.allowed_tables and t_name not in cte_names:
                raise SecurityViolationError(
                    f"Unauthorized table access: '{t_name}'. Allowed: {sorted(self.allowed_tables)}"
                )

        # 7. Block anonymous or unapproved functions
        for node in root.walk():
            if isinstance(node, exp.Anonymous):
                fn_name = node.name.lower()
                raise SecurityViolationError(
                    f"Prohibited or unregistered function call: '{fn_name}'"
                )

        # 8. Return standardized sanitized SQL string
        return root.sql(dialect=self.dialect)

    def is_safe(self, sql_query: str) -> bool:
        """Convenience method returning True if safe, False otherwise."""
        try:
            self.validate_and_sanitize(sql_query)
            return True
        except SecurityViolationError:
            return False

