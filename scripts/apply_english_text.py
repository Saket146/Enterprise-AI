"""
Replace the placeholder ("lorem ipsum") text of company policies and project
documents with English text.

Run it once from the project folder, with the backend's Python environment active:

    python scripts/apply_english_text.py

What it does:
  * policies.description  <- a full English policy for each policy name
  * documents.content     <- an English document built from the real project record
It reads the database address from backend/.env, changes only those two columns,
and can be run again safely (it always writes the same text).

Options:
    --csv   also update synthetic_data/csv/knowledge/policies.csv and documents.csv
            so that a database rebuilt from the CSV files gets the English text too

If you use Qdrant, rebuild the document search index afterwards (Operations Center >
"Rebuild index"), because it still holds the old text.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from sqlalchemy import create_engine, text  # noqa: E402

from app.configuration.config import settings  # noqa: E402
from knowledge_text import document_text, policy_text  # noqa: E402

POLICY_QUERY = """
    SELECT p.policy_id, p.policy_name, p.version, p.effective_date, d.department_name
    FROM policies p
    LEFT JOIN departments d ON d.department_id = p.department_id
    ORDER BY p.policy_id
"""

DOCUMENT_QUERY = """
    SELECT doc.document_id, doc.title, doc.document_type, doc.created_at,
           pr.project_name, pr.project_code, pr.description AS project_description,
           pr.status AS project_status, pr.priority AS project_priority,
           pr.start_date, pr.end_date,
           c.company_name AS client,
           dep.department_name AS department,
           TRIM(CONCAT(m.first_name, ' ', m.last_name)) AS manager,
           TRIM(CONCAT(a.first_name, ' ', a.last_name)) AS author
    FROM documents doc
    LEFT JOIN projects pr ON pr.project_id = doc.project_id
    LEFT JOIN clients c ON c.client_id = pr.client_id
    LEFT JOIN departments dep ON dep.department_id = doc.department_id
    LEFT JOIN employees m ON m.employee_id = pr.project_manager_id
    LEFT JOIN employees a ON a.employee_id = doc.created_by
    ORDER BY doc.document_id
"""


def build_texts(conn):
    policies = {}
    for row in conn.execute(text(POLICY_QUERY)).mappings():
        policies[row["policy_id"]] = policy_text(
            row["policy_name"], row["department_name"], row["version"], row["effective_date"]
        )

    documents = {}
    for row in conn.execute(text(DOCUMENT_QUERY)).mappings():
        record = dict(row)
        record["created_on"] = row["created_at"].date().isoformat() if row["created_at"] else None
        for key in ("manager", "author"):
            record[key] = record[key] or None
        documents[row["document_id"]] = document_text(record)
    return policies, documents


def update_csv(path, id_column, text_column, texts):
    if not os.path.exists(path):
        print(f"  skipped (file not found): {path}")
        return
    csv.field_size_limit(10 ** 9)
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    changed = 0
    for row in rows:
        new_text = texts.get(int(row[id_column]))
        if new_text is not None:
            row[text_column] = new_text
            changed += 1
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  updated {changed} rows in {os.path.relpath(path, ROOT)}")


def main():
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        policies, documents = build_texts(conn)
        if not policies and not documents:
            print("No policies or documents were found in the database. Nothing was changed.")
            return

        conn.execute(
            text("UPDATE policies SET description = :body WHERE policy_id = :id"),
            [{"id": pid, "body": body} for pid, body in policies.items()] or [{"id": -1, "body": ""}],
        )
        conn.execute(
            text("UPDATE documents SET content = :body WHERE document_id = :id"),
            [{"id": did, "body": body} for did, body in documents.items()] or [{"id": -1, "body": ""}],
        )
    print(f"Database updated: {len(policies)} policies and {len(documents)} documents now have English text.")

    if "--csv" in sys.argv:
        print("Updating CSV files:")
        folder = os.path.join(ROOT, "synthetic_data", "csv", "knowledge")
        update_csv(os.path.join(folder, "policies.csv"), "policy_id", "description", policies)
        update_csv(os.path.join(folder, "documents.csv"), "document_id", "content", documents)

    print("Done. If Qdrant is running, rebuild the document search index from the Operations Center.")


if __name__ == "__main__":
    main()
