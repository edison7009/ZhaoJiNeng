# Sync OpenRouter Models Workflow

This workflow describes how to update the LLM Leaderboard (`models.html`) using the synchronization script.
Due to the lack of an official daily/weekly/monthly ranking API from OpenRouter, we use a local Python script to fetch the latest available models, compute simulated scores based on context windows and provider tiers, and generate realistic ranking JSON files.

## Prerequisites
- Python 3.x installed
- Stable internet connection

## Steps to Sync Data

### 1. Run the Synchronization Script
Navigate to the root directory of the project and execute the Python sync script:
```powershell
python sync_openrouter_models.py
```

### 2. Verify Data Generation
Check the terminal output. It should indicate successful fetch and processing, similar to:
```
[20:39:04] Fetching models from OpenRouter...
[20:39:05] Processing 343 models into rankings...
[20:39:05] Rankings successfully saved to public/models_ranking.json
```
Ensure that `public/models_ranking.json` has been updated with the current timestamp.

### 3. Test Locally (Optional)
If you are running a local dev server, navigate to `/models.html` and verify that the models populate correctly across the `Day`, `Week`, and `Month` tabs.

### 4. Commit and Push
Commit the generated `.json` file to the repository.
```powershell
// turbo
git add public/models_ranking.json
git commit -m "data: sync openrouter models ranking YYYY-MM-DD"
git push origin main
```
This will trigger the automatic Cloudflare Pages deployment to update the live website.
