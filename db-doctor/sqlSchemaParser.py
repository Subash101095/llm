import sqlparse
import re

def parse_schema_sql(file_path: str):
    """
    Parse schema.sql into JSON-like structure.
    Supports:
    - Columns with types
    - Primary keys (inline + table-level)
    - Foreign keys (inline + table-level)
    - Indexes (KEY, UNIQUE KEY, INDEX)
    """
    with open(file_path, "r") as f:
        sql_content = f.read()

    statements = sqlparse.split(sql_content)
    schema_data = {"tables": []}

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt.upper().startswith("CREATE TABLE"):
            continue

        # Extract table name
        table_match = re.search(r"CREATE TABLE\s+`?(\w+)`?", stmt, re.IGNORECASE)
        if not table_match:
            continue
        table_name = table_match.group(1)

        table_info = {"name": table_name, "columns": [], "indexes": []}

        # Extract column + constraint section inside (...)
        inner_match = re.search(r"\((.*)\)", stmt, re.DOTALL)
        if not inner_match:
            continue
        inner_body = inner_match.group(1)

        # Split by commas at top level (not inside parentheses)
        parts = []
        depth = 0
        current = []
        for char in inner_body:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        if current:
            parts.append("".join(current).strip())

        for part in parts:
            # Column definition
            col_match = re.match(r"`(\w+)`\s+([\w()]+)", part)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                col_info = {"name": col_name, "type": col_type}

                if "PRIMARY KEY" in part.upper():
                    col_info["primary_key"] = True
                if "REFERENCES" in part.upper():
                    fk_match = re.search(r"REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)", part, re.IGNORECASE)
                    if fk_match:
                        fk_table, fk_col = fk_match.groups()
                        col_info["foreign_key"] = f"{fk_table}({fk_col})"

                table_info["columns"].append(col_info)
                continue

            # Table-level primary key
            if part.upper().startswith("PRIMARY KEY"):
                pk_match = re.findall(r"`(\w+)`", part)
                for pk in pk_match:
                    for c in table_info["columns"]:
                        if c["name"] == pk:
                            c["primary_key"] = True

            # Table-level foreign key
            if part.upper().startswith("CONSTRAINT") or part.upper().startswith("FOREIGN KEY"):
                fk_match = re.search(
                    r"FOREIGN KEY\s*\(`?(\w+)`?\)\s+REFERENCES\s+`?(\w+)`?\s*\(`?(\w+)`?\)",
                    part, re.IGNORECASE
                )
                if fk_match:
                    col, ref_table, ref_col = fk_match.groups()
                    for c in table_info["columns"]:
                        if c["name"] == col:
                            c["foreign_key"] = f"{ref_table}({ref_col})"

            # Indexes (KEY, UNIQUE KEY, INDEX)
            if part.upper().startswith("UNIQUE KEY") or part.upper().startswith("KEY") or part.upper().startswith("INDEX"):
                idx_name_match = re.match(r"(?:UNIQUE\s+)?KEY\s+`?(\w+)`?", part, re.IGNORECASE)
                idx_name = idx_name_match.group(1) if idx_name_match else None
                idx_cols = re.findall(r"`(\w+)`", part)

                idx_info = {
                    "name": idx_name or "unnamed_index",
                    "columns": idx_cols,
                    "unique": part.upper().startswith("UNIQUE KEY")
                }
                table_info["indexes"].append(idx_info)

        schema_data["tables"].append(table_info)

    return schema_data
