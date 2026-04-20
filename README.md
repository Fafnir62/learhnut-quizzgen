# LearnHut Quiz Generator AI (Streamlit Showcase)

Streamlit app that:

- uploads a PDF (lecture script, notes, etc.),
- dissects it into main fields/sections with keypoints + structure,
- generates exactly 4 MCQs per field (4 options, 1 correct),
- supports answer checking with green/red feedback and retry flow.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Environment

Create `.env`:

```env
OPENAI_API_KEY=your_key_here
```

## Streamlit Cloud Deployment

1. Push this repo to GitHub.
2. In Streamlit Cloud, create a new app from the repo.
3. Set `OPENAI_API_KEY` in Streamlit app Secrets.
4. Main file path: `app.py`.

## Notes

- Best results come from text-based PDFs (not scanned image-only PDFs).
- The app truncates very long PDF text for faster response times.
