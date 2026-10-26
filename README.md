\# Document API



A small API that accepts `.txt` and `.pdf` files, checks them, and saves them.



\## Requirements



\- Python 3.12

\- uv



\## Setup



Install the project tools:



&#x20;   uv sync



Copy the sample settings file:



&#x20;   Copy-Item config.example.env .env



\## Run the app



&#x20;   uv run uvicorn app.main:app --reload --no-access-log



Open http://127.0.0.1:8000/docs in your browser.



\## Run the tests



&#x20;   uv run pytest



\## Upload a file



Replace `notes.txt` with the path to your own text or PDF file:



&#x20;   curl.exe -F "file=@notes.txt" -F "title=My notes" http://127.0.0.1:8000/documents


------------------------------------------------------------------------------------------------------------------------------------------

## Phase 4 evaluation

Run the API, PostgreSQL, and Ollama first. From the project folder, run:

```powershell
uv run python docs/run_phase4.py