# NorthStar Assignment Pack

This workspace now contains a submission-ready draft for the NorthStar Databases and Analytics assignment.

## Main Files

- `report/northstar_assignment_report.md`
  Main report source with findings, interpretation, MongoDB design, and optimisation strategy.
- `report/northstar_assignment_report.docx`
  Word version generated from the report source.
- `notebooks/01_northstar_sql_r_analytics.ipynb`
  SQL in R workflow for relational loading, querying, and visualisation. This notebook has been executed locally.
- `notebooks/02_northstar_python_mongodb_solution.ipynb`
  Python analytics plus MongoDB Atlas design and indexing workflow. This notebook has been executed locally with a MongoDB-compatible fallback client when no live Atlas URI is present.
- `notebooks/html/01_northstar_sql_r_analytics.html`
  Executed HTML export of the R notebook.
- `notebooks/html/02_northstar_python_mongodb_solution.html`
  Executed HTML export of the Python/MongoDB notebook.
- `notebooks/html/01_northstar_sql_r_analytics.png`
  Screenshot of the executed R notebook.
- `notebooks/html/02_northstar_python_mongodb_solution.png`
  Screenshot of the executed Python/MongoDB notebook.

## Supporting Evidence

- `artifacts/northstar_analysis.db`
  SQLite database with cleaned analytical views.
- `artifacts/outputs/*.csv`
  Exported summary tables used in the report.
- `artifacts/outputs/*.svg`
  Exported charts for hub risk, maintenance failure, and missing delivery records.
- `build_northstar_artifacts.py`
  Rebuild script for the SQLite database, CSV summaries, and SVG charts.
- `mongodb-atlas-cli/bin/atlas`
  Official Atlas CLI binary downloaded locally.
- `.envs/northstar`
  Local runtime containing Python, Jupyter, and R used to execute the notebooks.

## Before Submission

1. Add your student ID to the report.
2. Review the `.docx` formatting and adjust headings or page layout if needed.
3. Push this local Git repository to GitHub once GitHub authentication is available on this machine.
4. Add the GitHub repository link into the report.
5. If a live MongoDB Atlas cluster is required, run the notebook again with `MONGODB_URI` set after Atlas authentication is available.
