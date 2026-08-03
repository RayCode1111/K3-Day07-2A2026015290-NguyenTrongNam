# Benchmark Queries - K3 VinUni Corpus

Use these 5 English benchmark questions for every team member when comparing retrieval strategies.

| # | query | gold_answer | expected_doc_id | metadata_filter |
|---|---|---|---|---|
| 1 | Which office must full-time undergraduate students register courses with, and what conditions must registration satisfy? | Students must register courses with the Office of Registrar. Registration must fit program requirements and prerequisite rules. | `vinuni-academic-regulations-undergrad` | none |
| 2 | How many library items may undergraduate students borrow, and for how long? | Undergraduate students may borrow 3 items for 2 weeks with 1 renewal. | `vinuni-library-access-services` | none |
| 3 | What is the overdue fine for normal library materials? | The normal material overdue fine is 10,000 VND per day per document. | `vinuni-financial-regulations-student` | none |
| 4 | What GPA is required to renew a full or 100% scholarship? | Full and 100% scholarships require a cumulative GPA of at least 3.2 for the academic year under evaluation, good disciplinary standing, and completion of the E.X.C.E.L self-evaluation plus advisor meeting. | `vinuni-scholarship-maintenance` | none |
| 5 | With `metadata_filter={"audience": "student"}`, are first-year students required to live in the VinUni dormitory? | Yes. All first-year students are required to reside in the VinUni dormitory as part of community-building objectives. | `vinuni-residential-life` | `{"audience": "student"}` |

## Scoring

- 2 points: top-3 contains a relevant chunk and the agent answer is correct.
- 1 point: top-3 contains a relevant chunk, but the answer lacks detail or the relevant chunk is not top-1.
- 0 points: top-3 does not contain a relevant chunk.

## Suggested Run

```powershell
$env:LAB_DATA_DIR="data/k3_vinuni"
$env:EMBEDDING_PROVIDER="local"
python main.py "How many library items may undergraduate students borrow, and for how long?"
```
