# 3. Labels

Date: 2026-10-16
Status: Accepted

## Context
Every item (email) must carry at least one label. Some labels are predefined, users can add their own, and labels will eventually be assigned three ways: manually, by an AI classifier and by user-defined rules.

## Decision

1. **Many-to-many**: items and labels are linked through `item_labels`, so an item can have several labels (like Gmail), not one folder-style category.
2. **Two kinds of label** in one `labels` table, distinguished by `kind`:
   - `system`: predefined, seeded by an Alembic data migration, read-only through the API (cannot be renamed, recoloured or deleted).
   - `custom`: created, edited and deleted by the user.
3. **Unique names**: each label has a `slug` derived from its name (lowercase, non-alphanumerics collapsed to `-`). Slugs are unique, so names are unique case-insensitively and custom labels cannot shadow system ones. Slugs are used in item filters (`GET /items?label=work`).
4. **"At least one label" invariant** via the `unlabeled` system label:
   - New items get `unlabeled` on ingestion.
   - Adding any label removes `unlabeled`.
   - Removing the last label, or deleting a custom label that was an item's only label, puts `unlabeled` back.
   - `unlabeled` cannot be assigned or removed through the API.
   The invariant is enforced in `app/services/labels.py`; every write path goes through it.
5. **Provenance on each assignment**: `item_labels.assigned_by` (`system`, `manual`, `ai`, `rule`) and an optional `confidence` (0–1, for AI). The latest assignment of the same label wins, so a manual assignment overrides an earlier AI one. The service functions take `assigned_by`/`confidence` so the AI classifier and rules engine can reuse them later.

## Consequences

- AI classification and rules need no schema change: they call `add_item_label` with `AssignedBy.AI` / `AssignedBy.RULE`.
- Changing the set of predefined labels requires a new data migration.
- `PUT /items/{id}/labels` marks every label it sets as `manual`, including ones that were previously assigned by AI or a rule.
- Not yet handled: preventing AI or rules from re-adding a label the user explicitly removed. That will need a record of manual removals when those features are built.
