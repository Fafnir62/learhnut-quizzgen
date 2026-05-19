import html
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PasswordType, PdfReader
from pypdf.errors import (
    DependencyError,
    EmptyFileError,
    FileNotDecryptedError,
    PdfReadError,
    WrongPasswordError,
)


load_dotenv()

st.set_page_config(
    page_title="LearnHut | Quiz Generator AI",
    page_icon="📘",
    layout="wide",
)


APP_COLORS = {
    "background": "#f8f9ff",
    "surface_lowest": "#ffffff",
    "surface_low": "#eff4ff",
    "surface_high": "#dce9ff",
    "surface_highest": "#d3e4fe",
    "outline_variant": "#c2c6d2",
    "primary": "#00366d",
    "primary_container": "#0e4d92",
    "secondary": "#3e5f93",
    "secondary_container": "#a1c2fd",
    "tertiary": "#003e3f",
    "tertiary_container": "#005759",
    "success_bg": "#dcfce7",
    "success_border": "#15803d",
    "danger_bg": "#fee2e2",
    "danger_border": "#b91c1c",
    "neutral_bg": "#f3f4f6",
    "neutral_border": "#cbd5e1",
    "selected_bg": "#e0ecff",
    "selected_border": "#295ea4",
    "text_main": "#0b1c30",
    "text_muted": "#424751",
}

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_TEXT_CHARS = 120_000
MAX_FIELD_CONTEXT_CHARS = 12_000


class PdfExtractionError(Exception):
    """Raised when uploaded PDF text cannot be extracted safely."""


def inject_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --bg: {APP_COLORS["background"]};
    --surface-lowest: {APP_COLORS["surface_lowest"]};
    --surface-low: {APP_COLORS["surface_low"]};
    --surface-high: {APP_COLORS["surface_high"]};
    --surface-highest: {APP_COLORS["surface_highest"]};
    --outline-variant: {APP_COLORS["outline_variant"]};
    --primary: {APP_COLORS["primary"]};
    --primary-container: {APP_COLORS["primary_container"]};
    --secondary: {APP_COLORS["secondary"]};
    --secondary-container: {APP_COLORS["secondary_container"]};
    --tertiary: {APP_COLORS["tertiary"]};
    --tertiary-container: {APP_COLORS["tertiary_container"]};
    --text-main: {APP_COLORS["text_main"]};
    --text-muted: {APP_COLORS["text_muted"]};
    --neutral-bg: {APP_COLORS["neutral_bg"]};
    --neutral-border: {APP_COLORS["neutral_border"]};
}}

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: var(--text-main);
}}

h1, h2, h3, h4 {{
    font-family: 'Manrope', sans-serif;
}}

[data-testid="stMainBlockContainer"] {{
    max-width: 1200px;
    padding-left: 2.6rem;
    padding-right: 2.6rem;
}}

section.main > div.block-container {{
    max-width: 1200px;
    padding-left: 2.6rem;
    padding-right: 2.6rem;
}}

.stApp {{
    background: radial-gradient(circle at 8% 20%, rgba(168,200,255,0.22) 0%, rgba(248,249,255,1) 38%),
                radial-gradient(circle at 92% 85%, rgba(125,245,248,0.16) 0%, rgba(248,249,255,1) 40%);
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stToolbar"] {{
    visibility: hidden;
    height: 0%;
}}

.top-nav {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(239, 244, 255, 0.82);
    border: 1px solid rgba(194, 198, 210, 0.42);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    padding: 12px 18px;
    margin-bottom: 1.2rem;
}}

.brand {{
    display: flex;
    align-items: center;
    gap: 10px;
}}

.brand-name {{
    font-family: 'Manrope', sans-serif;
    font-weight: 800;
    color: var(--primary);
    letter-spacing: -0.02em;
    font-size: 1.5rem;
}}

.brand-pill {{
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--secondary);
    background: var(--surface-high);
    border-radius: 999px;
    padding: 4px 10px;
}}

.hero {{
    text-align: center;
    background: linear-gradient(130deg, #ffffff 0%, #eff4ff 100%);
    border: 1px solid rgba(194, 198, 210, 0.4);
    border-radius: 24px;
    padding: 2.2rem 1.2rem;
    box-shadow: 0 12px 32px rgba(11, 28, 48, 0.07);
}}

.hero-pill {{
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #002021;
    background: #7df5f8;
    padding: 0.28rem 0.8rem;
    border-radius: 999px;
    margin-bottom: 0.9rem;
}}

.hero h1 {{
    font-size: clamp(2rem, 2.7vw, 3rem);
    line-height: 1.12;
    margin: 0;
    color: var(--primary);
    font-weight: 800;
}}

.hero p {{
    margin-top: 0.8rem;
    color: var(--secondary);
    font-size: 1rem;
}}

.card {{
    background: var(--surface-lowest);
    border: 1px solid rgba(194, 198, 210, 0.35);
    border-radius: 20px;
    padding: 1rem 1rem;
    box-shadow: 0 12px 28px rgba(11, 28, 48, 0.06);
}}

.field-title {{
    font-size: 1.14rem;
    font-weight: 800;
    color: var(--primary);
    margin: 0;
}}

.label {{
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--tertiary-container);
    background: #e6fffe;
    padding: 3px 8px;
    border-radius: 999px;
    margin-bottom: 8px;
}}

.muted {{
    color: var(--text-muted);
    font-size: 0.94rem;
}}

.option-box {{
    border-radius: 14px;
    padding: 11px 14px;
    border: 1px solid var(--neutral-border);
    background: var(--neutral-bg);
    color: var(--text-main);
    font-size: 0.95rem;
    font-weight: 500;
    line-height: 1.35;
}}

.option-letter {{
    display: inline-flex;
    width: 24px;
    height: 24px;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 700;
    border-radius: 999px;
    margin-right: 10px;
}}

.opt-neutral {{
    background: {APP_COLORS["neutral_bg"]};
    border-color: {APP_COLORS["neutral_border"]};
}}

.opt-neutral .option-letter {{
    background: #e2e8f0;
}}

.opt-selected {{
    background: {APP_COLORS["selected_bg"]};
    border-color: {APP_COLORS["selected_border"]};
}}

.opt-selected .option-letter {{
    background: #bfdbfe;
}}

.opt-correct {{
    background: {APP_COLORS["success_bg"]};
    border-color: {APP_COLORS["success_border"]};
}}

.opt-correct .option-letter {{
    background: #86efac;
}}

.opt-wrong {{
    background: {APP_COLORS["danger_bg"]};
    border-color: {APP_COLORS["danger_border"]};
}}

.opt-wrong .option-letter {{
    background: #fecaca;
}}

.kpi-list {{
    margin: 0;
    padding-left: 1rem;
}}

.kpi-list li {{
    margin-bottom: 4px;
    color: var(--text-muted);
    font-size: 0.93rem;
}}

.footer-note {{
    text-align: center;
    color: var(--secondary);
    font-size: 0.78rem;
    margin-top: 1.5rem;
}}

[data-testid="stFileUploaderDropzone"] {{
    border-radius: 20px;
    border: 2px dashed rgba(194, 198, 210, 0.6);
    background: var(--surface-lowest);
    padding-top: 1.2rem;
    padding-bottom: 1.2rem;
}}

div.stButton > button {{
    border-radius: 12px;
    font-weight: 700;
    border: 1px solid transparent;
}}

div.stButton > button[kind="primary"] {{
    background: var(--primary);
    color: #fff;
}}

div.stButton > button[kind="secondary"] {{
    background: var(--surface-high);
    color: var(--text-main);
    border-color: rgba(194,198,210,0.5);
}}

.small-pick button {{
    min-height: 1.9rem !important;
    padding: 0.15rem 0.45rem !important;
    font-size: 0.72rem !important;
    border-radius: 10px !important;
}}

@media (max-width: 900px) {{
    [data-testid="stMainBlockContainer"],
    section.main > div.block-container {{
        padding-left: 1rem;
        padding-right: 1rem;
    }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    defaults = {
        "analysis": None,
        "pdf_text": "",
        "pdf_title": "",
        "file_fingerprint": "",
        "field_quizzes": {},
        "quiz_progress": {},
        "quiz_checked": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


@st.cache_data(show_spinner=False)
def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            decrypt_result = reader.decrypt("")
            if decrypt_result == PasswordType.NOT_DECRYPTED:
                raise PdfExtractionError(
                    "Dieses PDF ist passwortgeschuetzt. Bitte lade eine unverschluesselte Version hoch."
                )

        all_pages: List[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                all_pages.append(page_text)
    except DependencyError as exc:
        raise PdfExtractionError(
            "Dieses PDF ist verschluesselt. Auf dem Server fehlt die pypdf-Krypto-Unterstuetzung. "
            "Deploye die App nach dem requirements.txt-Update bitte neu."
        ) from exc
    except (WrongPasswordError, FileNotDecryptedError) as exc:
        raise PdfExtractionError(
            "Dieses PDF ist passwortgeschuetzt. Bitte lade eine unverschluesselte Version hoch."
        ) from exc
    except (EmptyFileError, PdfReadError) as exc:
        raise PdfExtractionError(
            "Dieses PDF konnte nicht gelesen werden. Bitte pruefe die Datei und versuche es erneut."
        ) from exc

    merged = "\n\n".join(all_pages)
    return re.sub(r"\n{3,}", "\n\n", merged).strip()


def sanitize_id(text: str, fallback: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    if not token:
        token = fallback
    return token[:48]


def compact_text(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[Content truncated for speed.]"


def safe_json_loads(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_response_text(response: Any) -> str:
    direct = getattr(response, "output_text", "")
    if direct:
        return direct

    chunks: List[str] = []
    for item in getattr(response, "output", []):
        for content in getattr(item, "content", []):
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def llm_json(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
        temperature=0.0,
        text={
            "format": {
                "type": "json_schema",
                "name": "structured_output",
                "strict": True,
                "schema": schema,
            }
        },
    )
    parsed = extract_response_text(response)
    return safe_json_loads(parsed)


def select_relevant_context(pdf_text: str, field: Dict[str, Any], limit_chars: int = MAX_FIELD_CONTEXT_CHARS) -> str:
    passages = [p.strip() for p in re.split(r"\n\s*\n", pdf_text) if p.strip()]
    if not passages:
        return compact_text(pdf_text, limit=limit_chars)

    keywords_raw: List[str] = [field.get("name", "")]
    keywords_raw.extend(field.get("keypoints", []))
    keywords_raw.extend(field.get("big_points", []))
    keywords_raw.extend(field.get("structure", []))

    keyword_tokens = set()
    for item in keywords_raw:
        for token in re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", item.lower()):
            keyword_tokens.add(token)

    if not keyword_tokens:
        return compact_text(pdf_text, limit=limit_chars)

    scored: List[Any] = []
    for passage in passages:
        tokens = set(re.findall(r"[A-Za-zÄÖÜäöüß0-9]{4,}", passage.lower()))
        overlap = len(tokens & keyword_tokens)
        if overlap > 0:
            scored.append((overlap, len(passage), passage))

    if not scored:
        return compact_text(pdf_text, limit=limit_chars)

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected_passages: List[str] = []
    total = 0
    for _, _, passage in scored:
        if total >= limit_chars:
            break
        remaining = limit_chars - total
        if remaining <= 0:
            break
        clipped = passage[:remaining]
        selected_passages.append(clipped)
        total += len(clipped) + 2

    return "\n\n".join(selected_passages).strip()


def dissect_pdf_into_fields(client: OpenAI, model: str, pdf_text: str) -> Dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "document_title": {"type": "string"},
            "fields": {
                "type": "array",
                "minItems": 3,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "summary": {"type": "string"},
                        "keypoints": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 8,
                            "items": {"type": "string"},
                        },
                        "big_points": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 6,
                            "items": {"type": "string"},
                        },
                        "structure": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 10,
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "name",
                        "summary",
                        "keypoints",
                        "big_points",
                        "structure",
                    ],
                },
            },
        },
        "required": ["document_title", "fields"],
    }

    prompt = (
        "Analysiere den akademischen PDF-Inhalt und zerlege ihn in die wichtigsten Themenfelder/Abschnitte.\n"
        "Liefere pro Feld: kurze Zusammenfassung, Kernpunkte, große Ideen und Lernstruktur.\n"
        "Wichtig:\n"
        "- Nur Informationen aus dem PDF verwenden.\n"
        "- Knapp, präzise, in deutscher Sprache.\n"
        "- Keine Halluzinationen, keine freien Ergänzungen.\n\n"
        f"PDF-TEXT:\n{compact_text(pdf_text)}"
    )

    data = llm_json(
        client=client,
        model=model,
        system_prompt=(
            "Du bist ein wissenschaftlicher Tutor. Antworte nur mit validem JSON "
            "und folge exakt dem Schema."
        ),
        user_prompt=prompt,
        schema=schema,
    )

    cleaned_fields: List[Dict[str, Any]] = []
    used_ids = set()
    for i, field in enumerate(data.get("fields", []), start=1):
        base_id = sanitize_id(field.get("name", ""), f"field_{i}")
        unique_id = base_id
        suffix = 2
        while unique_id in used_ids:
            unique_id = f"{base_id}_{suffix}"
            suffix += 1
        used_ids.add(unique_id)

        cleaned_fields.append(
            {
                "id": unique_id,
                "name": field.get("name", f"Thema {i}"),
                "summary": field.get("summary", ""),
                "keypoints": field.get("keypoints", []),
                "big_points": field.get("big_points", []),
                "structure": field.get("structure", []),
            }
        )

    return {
        "document_title": data.get("document_title", "Unbenanntes Dokument"),
        "fields": cleaned_fields,
    }


def generate_quizzes_for_field(
    client: OpenAI,
    model: str,
    field: Dict[str, Any],
    difficulty: str,
    field_context: str,
) -> List[Dict[str, Any]]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "minItems": 4,
                            "maxItems": 4,
                            "items": {"type": "string"},
                        },
                        "correct_option_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                        },
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "question",
                        "options",
                        "correct_option_index",
                        "explanation",
                    ],
                },
            }
        },
        "required": ["questions"],
    }

    prompt = (
        "Erstelle genau 4 Multiple-Choice-Fragen zu diesem Themenfeld.\n"
        "Regeln:\n"
        "- Genau 4 Antwortoptionen pro Frage.\n"
        "- Genau 1 Option ist korrekt.\n"
        "- Sprache: Deutsch.\n"
        "- Inhaltlich nur auf Basis der bereitgestellten Quellenausschnitte.\n"
        "- Keine mehrdeutigen oder trickreichen Antworten.\n"
        f"- Schwierigkeitsgrad: {difficulty}\n\n"
        f"THEMENFELD: {field['name']}\n"
        f"ZUSAMMENFASSUNG: {field['summary']}\n"
        f"KERNPUNKTE: {json.dumps(field['keypoints'], ensure_ascii=True)}\n"
        f"GROSSE IDEEN: {json.dumps(field['big_points'], ensure_ascii=True)}\n"
        f"STRUKTUR: {json.dumps(field['structure'], ensure_ascii=True)}\n\n"
        f"RELEVANTE QUELLENAUSSCHNITTE:\n{field_context}"
    )

    data = llm_json(
        client=client,
        model=model,
        system_prompt=(
            "Du bist ein praeziser Autor fuer universitaere Quizfragen. "
            "Nur JSON zurueckgeben, keine Mehrdeutigkeit."
        ),
        user_prompt=prompt,
        schema=schema,
    )
    return data.get("questions", [])


@st.cache_data(show_spinner=False, ttl=86_400)
def cached_dissect_pdf_into_fields(model: str, pdf_text: str) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt.")
    client = OpenAI(api_key=api_key)
    return dissect_pdf_into_fields(client=client, model=model, pdf_text=pdf_text)


@st.cache_data(show_spinner=False, ttl=86_400)
def cached_generate_quizzes_for_field(
    model: str,
    field_json: str,
    difficulty: str,
    field_context: str,
) -> List[Dict[str, Any]]:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt.")
    client = OpenAI(api_key=api_key)
    field = json.loads(field_json)
    return generate_quizzes_for_field(
        client=client,
        model=model,
        field=field,
        difficulty=difficulty,
        field_context=field_context,
    )


def option_state_class(
    selected_idx: Optional[int],
    option_idx: int,
    correct_idx: int,
    checked: bool,
    locked: bool,
) -> str:
    if locked and option_idx == correct_idx:
        return "opt-correct"
    if checked:
        if option_idx == correct_idx:
            return "opt-correct"
        if selected_idx == option_idx and selected_idx != correct_idx:
            return "opt-wrong"
        return "opt-neutral"
    if selected_idx == option_idx:
        return "opt-selected"
    return "opt-neutral"


def render_quiz_question(
    field_id: str,
    q_idx: int,
    question: Dict[str, Any],
    progress: Dict[str, Any],
) -> None:
    selected = progress.get("selected")
    checked = progress.get("checked", False)
    locked = progress.get("locked", False)
    correct_idx = question["correct_option_index"]

    st.markdown(f"**Frage {q_idx + 1:02d}**")
    st.markdown(
        f"<div class='muted' style='font-size:1rem;color:{APP_COLORS['text_main']};"
        f"font-weight:600;margin-bottom:8px'>{html.escape(question['question'])}</div>",
        unsafe_allow_html=True,
    )

    for opt_idx, option in enumerate(question["options"]):
        css_class = option_state_class(selected, opt_idx, correct_idx, checked, locked)
        cols = st.columns([12, 1], vertical_alignment="center")
        with cols[0]:
            st.markdown(
                f"<div class='option-box {css_class}'>"
                f"<span class='option-letter'>{chr(65 + opt_idx)}</span>"
                f"{html.escape(option)}</div>",
                unsafe_allow_html=True,
            )
        with cols[1]:
            if locked:
                st.button("✓", key=f"lock_{field_id}_{q_idx}_{opt_idx}", disabled=True, use_container_width=False)
            else:
                selected_now = selected == opt_idx
                st.markdown("<div class='small-pick'>", unsafe_allow_html=True)
                clicked = st.button(
                    "Gewahlt" if selected_now else "Wahlen",
                    key=f"pick_{field_id}_{q_idx}_{opt_idx}",
                    use_container_width=False,
                    type="secondary" if selected_now else "primary",
                )
                st.markdown("</div>", unsafe_allow_html=True)
                if clicked:
                    progress["selected"] = opt_idx
                    progress["checked"] = False
                    st.rerun()

    if checked and selected is not None and selected == correct_idx:
        st.success(f"Richtig. {question['explanation']}")
    elif checked and selected is not None and selected != correct_idx:
        st.error(f"Falsch. {question['explanation']}")
    elif checked and selected is None:
        st.warning("Noch keine Antwort ausgewaehlt.")


def render_top_nav() -> None:
    st.markdown(
        """
<div class="top-nav">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
    <div class="brand">
      <div class="brand-name">LearnHut</div>
      <div class="brand-pill">Quiz-Generator KI</div>
    </div>
    <div style="font-size:0.9rem;color:#3e5f93;font-weight:600;">
      Professoren-Demo • Streamlit-bereit
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
<section class="hero">
  <div class="hero-pill">KI-Unterstuetztes Lernen</div>
  <h1>PDF hochladen, Themen automatisch zerlegen, Quizfragen sofort erhalten</h1>
  <p>Lade dein Vorlesungsskript hoch, lasse Hauptfelder analysieren und erzeuge pro Feld 4 hochwertige Multiple-Choice-Fragen.</p>
</section>
""",
        unsafe_allow_html=True,
    )


def render_field_card(field: Dict[str, Any], model: str, difficulty: str, pdf_text: str) -> None:
    field_id = field["id"]
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='label'>Themenfeld</div>", unsafe_allow_html=True)
    st.markdown(f"<h3 class='field-title'>{html.escape(field['name'])}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p class='muted'>{html.escape(field['summary'])}</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Kernpunkte**")
        st.markdown(
            "<ul class='kpi-list'>" + "".join(
                f"<li>{html.escape(item)}</li>" for item in field["keypoints"]
            ) + "</ul>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("**Grosse Ideen**")
        st.markdown(
            "<ul class='kpi-list'>" + "".join(
                f"<li>{html.escape(item)}</li>" for item in field["big_points"]
            ) + "</ul>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown("**Struktur**")
        st.markdown(
            "<ul class='kpi-list'>" + "".join(
                f"<li>{html.escape(item)}</li>" for item in field["structure"]
            ) + "</ul>",
            unsafe_allow_html=True,
        )

    quiz_button_label = f"4 Quizfragen zu '{field['name']}' erzeugen"
    if st.button(
        quiz_button_label,
        key=f"gen_{field_id}",
        use_container_width=True,
        type="primary",
    ):
        if not get_api_key():
            st.error("OPENAI_API_KEY fehlt in der .env.")
        else:
            with st.spinner(f"Quizfragen fuer {field['name']} werden erstellt..."):
                field_context = select_relevant_context(pdf_text, field)
                questions = cached_generate_quizzes_for_field(
                    model=model,
                    field_json=json.dumps(field, ensure_ascii=True, sort_keys=True),
                    difficulty=difficulty,
                    field_context=field_context,
                )
            st.session_state.field_quizzes[field_id] = questions
            st.session_state.quiz_progress[field_id] = [
                {"selected": None, "checked": False, "locked": False} for _ in questions
            ]
            st.session_state.quiz_checked[field_id] = False
            st.success("4 Quizfragen erstellt.")

    questions = st.session_state.field_quizzes.get(field_id, [])
    progress_list = st.session_state.quiz_progress.get(field_id, [])

    if questions and progress_list:
        st.markdown("---")
        st.markdown("### Quiz-Vorschau")
        for q_idx, q in enumerate(questions):
            render_quiz_question(
                field_id=field_id,
                q_idx=q_idx,
                question=q,
                progress=progress_list[q_idx],
            )
            st.markdown("")

        col_check, col_retry = st.columns([1, 1])
        with col_check:
            if st.button(
                "Antworten pruefen",
                key=f"check_{field_id}",
                use_container_width=True,
                type="primary",
            ):
                any_wrong = False
                for idx, q in enumerate(questions):
                    prog = progress_list[idx]
                    if prog["locked"]:
                        continue
                    prog["checked"] = True
                    if prog["selected"] == q["correct_option_index"]:
                        prog["locked"] = True
                    else:
                        any_wrong = True

                st.session_state.quiz_checked[field_id] = True

                if any_wrong:
                    st.warning(
                        "Einige Antworten sind falsch oder leer. Falsche Auswahl wird rot, richtige gruen."
                    )
                else:
                    st.success("Alle Antworten in diesem Themenfeld sind korrekt.")
                st.rerun()

        all_locked = all(p.get("locked") for p in progress_list)
        has_retry_candidates = any(not p.get("locked") for p in progress_list)

        with col_retry:
            if st.session_state.quiz_checked.get(field_id, False) and has_retry_candidates:
                if st.button(
                    "Falsche/Leere wiederholen",
                    key=f"retry_{field_id}",
                    use_container_width=True,
                    type="secondary",
                ):
                    for prog in progress_list:
                        if not prog["locked"]:
                            prog["selected"] = None
                            prog["checked"] = False
                    st.info("Falsche/leere Antworten wurden zurueckgesetzt. Korrekte bleiben gruen gesperrt.")
                    st.rerun()

        if all_locked:
            st.success("Perfekt in diesem Themenfeld. Keine Wiederholung mehr noetig.")

    st.markdown("</div>", unsafe_allow_html=True)


def main() -> None:
    inject_css()
    ensure_state()
    render_top_nav()
    render_hero()

    model = DEFAULT_MODEL

    st.markdown("## Upload & Einstellungen")
    uploader_col, settings_col = st.columns([2, 1], gap="large")

    with uploader_col:
        uploaded_pdf = st.file_uploader(
            "PDF hier hochladen",
            type=["pdf"],
            help="Vorlesungsskripte oder Lernmaterial als PDF hochladen.",
        )

    with settings_col:
        difficulty = st.selectbox(
            "Schwierigkeitsgrad",
            ["Grundlagen (Leicht)", "Mittel", "Fortgeschritten (Wissenschaftlich)"],
            index=1,
        )
        st.caption("Fragen pro Themenfeld: 4 (fest)")

    if uploaded_pdf is None:
        st.info("Lade ein PDF hoch, um mit der Analyse zu starten.")
        st.markdown("<div class='footer-note'>© 2026 LearnHut Academic Architect</div>", unsafe_allow_html=True)
        return

    file_bytes = uploaded_pdf.read()
    fingerprint = f"{uploaded_pdf.name}:{len(file_bytes)}"
    if st.session_state.file_fingerprint != fingerprint:
        st.session_state.file_fingerprint = fingerprint
        st.session_state.analysis = None
        st.session_state.pdf_text = ""
        st.session_state.pdf_title = ""
        st.session_state.field_quizzes = {}
        st.session_state.quiz_progress = {}
        st.session_state.quiz_checked = {}

    if not st.session_state.pdf_text:
        with st.spinner("Text wird aus dem PDF extrahiert..."):
            try:
                extracted = extract_pdf_text(file_bytes)
            except PdfExtractionError as exc:
                st.error(str(exc))
                return
        st.session_state.pdf_text = extracted
        st.session_state.pdf_title = uploaded_pdf.name.rsplit(".", 1)[0]

    if not st.session_state.pdf_text.strip():
        st.error("Text konnte nicht aus dem PDF extrahiert werden. Das PDF ist evtl. nur ein Scan/Bild.")
        return

    if st.button("PDF in Haupt-Themenfelder zerlegen", use_container_width=True, type="primary"):
        if not get_api_key():
            st.error("OPENAI_API_KEY fehlt in der .env.")
        else:
            with st.spinner("Struktur wird analysiert und Themenfelder werden extrahiert..."):
                st.session_state.analysis = cached_dissect_pdf_into_fields(
                    model=model,
                    pdf_text=st.session_state.pdf_text,
                )
            st.success("Themenfelder erfolgreich extrahiert.")

    analysis = st.session_state.analysis
    if analysis:
        title = analysis.get("document_title") or st.session_state.pdf_title
        st.markdown(f"## Vorschau: {html.escape(title)}")
        for field in analysis.get("fields", []):
            render_field_card(field, model=model, difficulty=difficulty, pdf_text=st.session_state.pdf_text)

    st.markdown("<div class='footer-note'>© 2026 LearnHut Academic Architect</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
