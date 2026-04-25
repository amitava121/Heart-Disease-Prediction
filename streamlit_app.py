from __future__ import annotations

import base64
import ast
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


class _SuppressComponentsHtmlDeprecation(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "Please replace `st.components.v1.html` with `st.iframe`." not in msg


streamlit_logger = logging.getLogger("streamlit")
streamlit_logger.addFilter(_SuppressComponentsHtmlDeprecation())
logging.getLogger("streamlit.deprecation_util").setLevel(logging.ERROR)


st.set_page_config(page_title="Clinical Ethereal", page_icon="❤️", layout="wide")

PROJECT_ROOT = Path(__file__).resolve().parent
CSV_CANDIDATE_PATHS = (
    PROJECT_ROOT / "data" / "framingham.csv",
    PROJECT_ROOT / "framingham.csv",
)
PREDICTION_THRESHOLD = 0.20
FEATURE_COLUMNS = [
    "male",
    "age",
    "currentSmoker",
    "cigsPerDay",
    "BPMeds",
    "prevalentStroke",
    "prevalentHyp",
    "diabetes",
    "totChol",
    "sysBP",
    "diaBP",
    "BMI",
    "heartRate",
    "glucose",
]

DEFAULT_DIRECTIVES = [
    {
        "title": "Immediate Beta-Blocker Review",
        "detail": "Schedule a consultation within 48 hours to evaluate current dosage relative to peak systolic pressure.",
    },
    {
        "title": "Cardio-Respiratory Fasting",
        "detail": "Initiate a 16:8 metabolic cycle to reduce systemic inflammation markers found in lipid sub-fractions.",
    },
    {
        "title": "Precision Magnesium Intake",
        "detail": "Supplement 400mg Glycinate daily to address muscular myocardial fatigue signatures.",
    },
]

DEFAULT_PHYSICIAN_NOTE = (
    "The elevated risk is primarily driven by arterial stiffness. "
    "While glucose is stable, the lipid profile requires pharmaceutical intervention."
)
PAGE_TEMPLATE_MAP = {
    "landing_page": PROJECT_ROOT / "frontend" / "landing_page" / "code.html",
    "prediction_dashboard": PROJECT_ROOT / "frontend" / "prediction_dashboard" / "code.html",
    "result_page": PROJECT_ROOT / "frontend" / "result_page" / "code.html",
    "health_insights": PROJECT_ROOT / "frontend" / "health_insights" / "code.html",
    "user_profile": PROJECT_ROOT / "frontend" / "user_profile" / "code.html",
}


def apply_chrome_cleanup() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            #MainMenu,
            footer {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
            }

            .stApp {
                background: #0e1322;
            }

            .main .block-container {
                max-width: 100% !important;
                padding-top: 0 !important;
                padding-bottom: 0 !important;
                padding-left: 0 !important;
                padding-right: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 100% !important;
                min-width: 100% !important;
                width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stElementContainer"] {
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stElementContainer"]:has(.ce-hidden-iframe),
            [data-testid="stElementContainer"]:has(.ce-cleanup-style) {
                height: 0 !important;
                min-height: 0 !important;
                max-height: 0 !important;
                flex: 0 0 0 !important;
                overflow: hidden !important;
                padding: 0 !important;
                margin: 0 !important;
                display: none !important;
            }

            [data-testid="stElementContainer"]:has(.ce-main-iframe) {
                height: 100vh !important;
                max-height: 100vh !important;
                min-height: 100vh !important;
                flex: 0 0 100vh !important;
                overflow: hidden !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stElementContainer"]:has(.ce-main-iframe) [data-testid="stMarkdownContainer"] {
                width: 100% !important;
                max-width: 100% !important;
                height: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            .ce-main-iframe {
                width: 100vw !important;
                height: 100vh !important;
                border: none !important;
                display: block !important;
            }

            [data-testid="stElementContainer"]:has(> iframe[data-testid="stIFrame"][scrolling="auto"]) {
                height: 100vh !important;
                max-height: 100vh !important;
                min-height: 100vh !important;
                flex: 0 0 100vh !important;
                overflow: hidden !important;
            }

            [data-testid="stElementContainer"]:has(> iframe[data-testid="stIFrame"][scrolling="no"]) {
                height: 0 !important;
                min-height: 0 !important;
                max-height: 0 !important;
                flex: 0 0 0 !important;
                overflow: hidden !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stAppViewContainer"] {
                padding: 0 !important;
                margin: 0 !important;
            }

            section.main {
                padding: 0 !important;
                margin: 0 !important;
            }

            [data-testid="stMain"] {
                padding: 0 !important;
                margin: 0 !important;
                align-items: stretch !important;
                overflow-x: hidden !important;
            }

            [data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }
        </style>
        <span class="ce-cleanup-style"></span>
        """,
        unsafe_allow_html=True,
    )


def get_page_key() -> str:
    raw = st.query_params.get("page", "landing_page")
    if isinstance(raw, list):
        raw = raw[0] if raw else "landing_page"
    key = str(raw).strip().lower()
    return key if key in PAGE_TEMPLATE_MAP else "landing_page"


def get_query_param(name: str, default: str = "") -> str:
    raw = st.query_params.get(name, default)
    if isinstance(raw, list):
        return str(raw[0]) if raw else default
    return str(raw)


@st.cache_resource(show_spinner=False)
def get_model_bundle() -> tuple[StandardScaler, LogisticRegression, dict[str, float]]:
    model_path = PROJECT_ROOT / "model_bundle.joblib"
    if not model_path.exists():
        raise FileNotFoundError(
            "model_bundle.joblib not found. Run 'python train_model.py' to train and save the model first."
        )
    bundle = joblib.load(model_path)
    return bundle["scaler"], bundle["model"], bundle["defaults"]


def parse_prediction_payload() -> dict[str, Any] | None:
    encoded = get_query_param("predict_payload")
    if not encoded:
        return None

    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _normalize_directives(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue

        title = str(
            item.get("title")
            or item.get("name")
            or item.get("heading")
            or item.get("action")
            or ""
        ).strip()
        detail = str(
            item.get("detail")
            or item.get("description")
            or item.get("recommendation")
            or item.get("rationale")
            or item.get("note")
            or ""
        ).strip()
        if not title or not detail:
            continue
        cleaned.append(
            {
                "title": title[:90],
                "detail": detail[:220],
            }
        )
        if len(cleaned) == 3:
            break

    while len(cleaned) < 3:
        cleaned.append(DEFAULT_DIRECTIVES[len(cleaned)].copy())

    return cleaned


def _extract_json_string(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?", "", trimmed).strip()
        trimmed = re.sub(r"```$", "", trimmed).strip()
    return trimmed


def _extract_candidate_text(parts: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for part in parts:
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            chunks.append(text)
            continue

        inline_data = part.get("inlineData") or part.get("inline_data")
        if isinstance(inline_data, dict):
            decoded = inline_data.get("data")
            if isinstance(decoded, str) and decoded.strip():
                chunks.append(decoded)

    return "\n".join(chunks).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = _extract_json_string(text)
    candidates: list[str] = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        try:
            parsed = ast.literal_eval(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

    return {}


def _get_gemini_api_key() -> str:
    env_key = os.getenv("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    try:
        secret_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        secret_key = ""
    return secret_key


def _build_local_ai_fallback(
    payload: dict[str, Any],
    probability_pct: float,
    risk_text: str,
) -> tuple[list[dict[str, str]], str]:
    def _num(name: str, default: float = 0.0) -> float:
        try:
            return float(payload.get(name, default))
        except (TypeError, ValueError):
            return default

    age = _num("age", 45)
    sys_bp = _num("sysBP", 120)
    dia_bp = _num("diaBP", 80)
    chol = _num("totChol", 180)
    bmi = _num("BMI", 25)
    hr = _num("heartRate", 72)
    glucose = _num("glucose", 90)

    directives: list[dict[str, str]] = []

    if sys_bp >= 140 or dia_bp >= 90:
        directives.append(
            {
                "title": "Blood Pressure Priority",
                "detail": "Track BP twice daily for 14 days and review trends with your doctor.",
            }
        )
    else:
        directives.append(
            {
                "title": "Maintain Blood Pressure",
                "detail": "Keep sodium moderate and continue weekly BP checks to sustain current control.",
            }
        )

    if chol >= 200:
        directives.append(
            {
                "title": "Lipid Reduction Plan",
                "detail": "Reduce saturated fats and arrange a fasting lipid panel follow-up in 8 weeks.",
            }
        )
    else:
        directives.append(
            {
                "title": "Lipid Maintenance",
                "detail": "Maintain heart-healthy diet and repeat cholesterol testing at routine checkups.",
            }
        )

    if bmi >= 30:
        directives.append(
            {
                "title": "Weight Risk Mitigation",
                "detail": "Target gradual weight loss with structured nutrition and 150 minutes activity weekly.",
            }
        )
    elif hr > 90:
        directives.append(
            {
                "title": "Heart Rate Optimization",
                "detail": "Prioritize hydration, sleep, and aerobic conditioning to lower resting heart rate.",
            }
        )
    elif glucose >= 110:
        directives.append(
            {
                "title": "Glycemic Monitoring",
                "detail": "Limit refined carbohydrates and recheck fasting glucose with your physician soon.",
            }
        )
    else:
        directives.append(
            {
                "title": "Lifestyle Reinforcement",
                "detail": "Continue balanced diet, regular activity, and preventive follow-up every 6-12 months.",
            }
        )

    note = (
        f"AI-generated summary: Estimated risk is {probability_pct:.1f}% ({risk_text}). "
        f"Age {int(round(age))}, BP {int(round(sys_bp))}/{int(round(dia_bp))}, cholesterol {int(round(chol))}, "
        f"BMI {bmi:.1f}, heart rate {int(round(hr))}, glucose {int(round(glucose))}. "
        "Please confirm this assessment with a licensed doctor."
    )

    return _normalize_directives(directives), note[:280]


def _fetch_gemini_directives(
    payload: dict[str, Any],
    probability_pct: float,
    risk_text: str,
) -> tuple[list[dict[str, str]], str]:
    api_key = _get_gemini_api_key()
    if not api_key:
        logging.warning("Gemini API key is not configured; using local AI fallback directives.")
        return _build_local_ai_fallback(payload, probability_pct, risk_text)

    compact_payload: dict[str, int | float] = {}
    always_include = {"age", "totChol", "sysBP", "diaBP", "BMI", "heartRate", "glucose", "cigsPerDay"}
    for key in FEATURE_COLUMNS:
        raw_value = payload.get(key)
        if raw_value is None or raw_value == "":
            continue
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            continue

        is_binary_flag = key in {"male", "currentSmoker", "BPMeds", "prevalentStroke", "prevalentHyp", "diabetes"}
        if key not in always_include and is_binary_flag and numeric == 0:
            continue

        compact_payload[key] = int(numeric) if numeric.is_integer() else round(numeric, 2)

    prompt = {
        "risk": f"{risk_text} ({round(probability_pct, 1)}%)",
        "patient_payload": compact_payload,
        "instructions": [
            "Return strict JSON only.",
            "Provide exactly 3 directives tailored to this patient payload.",
            "Directive title must be short and specific.",
            "Directive detail must be practical, specific, and <= 16 words.",
            "Physician note must be natural, clinically grounded, and <= 38 words.",
            "No markdown, no code fences, no extra keys.",
        ],
    }

    request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": json.dumps(prompt),
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "topP": 0.8,
            "topK": 20,
            "maxOutputTokens": 220,
            "responseSchema": {
                "type": "OBJECT",
                "required": ["directives", "physician_note"],
                "properties": {
                    "directives": {
                        "type": "ARRAY",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {
                            "type": "OBJECT",
                            "required": ["title", "detail"],
                            "properties": {
                                "title": {"type": "STRING"},
                                "detail": {"type": "STRING"},
                            },
                        },
                    },
                    "physician_note": {"type": "STRING"},
                },
            },
        },
    }

    relaxed_request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Return ONLY JSON with keys directives and physician_note. "
                            "directives must be exactly 3 objects with title and detail. "
                            f"Context: risk={risk_text} ({round(probability_pct, 1)}%), payload={json.dumps(compact_payload)}"
                        ),
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
            "topP": 0.8,
            "topK": 20,
            "maxOutputTokens": 220,
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )

    def _send_request(body: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            url=url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_parsed_candidate(response_data: dict[str, Any]) -> dict[str, Any]:
        candidates = response_data.get("candidates", [])
        if not candidates:
            return {}

        parts = candidates[0].get("content", {}).get("parts", [])
        text = _extract_candidate_text(parts)

        parsed: dict[str, Any] = {}
        if text:
            parsed = _parse_json_object(text)
        if parsed:
            return parsed

        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict):
                    parsed = _parse_json_object(json.dumps(part))
                    if parsed:
                        return parsed
        return {}

    for attempt in range(3):
        try:
            response_data = _send_request(request_body)
            parsed = _extract_parsed_candidate(response_data)

            if not parsed:
                response_data = _send_request(relaxed_request_body)
                parsed = _extract_parsed_candidate(response_data)

            if not parsed:
                raise ValueError("Gemini returned invalid JSON payload")

            raw_directives = (
                parsed.get("directives")
                or parsed.get("recommendations")
                or parsed.get("clinical_directives")
                or []
            )
            if isinstance(raw_directives, dict):
                raw_directives = [raw_directives]

            directives = _normalize_directives(raw_directives if isinstance(raw_directives, list) else [])
            physician_note = str(
                parsed.get("physician_note")
                or parsed.get("note")
                or parsed.get("summary")
                or parsed.get("clinical_note")
                or ""
            ).strip() or DEFAULT_PHYSICIAN_NOTE

            if directives == _normalize_directives(None):
                return _build_local_ai_fallback(payload, probability_pct, risk_text)

            return directives, physician_note[:280]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            logging.warning("Gemini directives request failed (attempt %s/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(2**attempt)

    logging.warning("Gemini directives unavailable; using local AI fallback directives.")
    return _build_local_ai_fallback(payload, probability_pct, risk_text)


def build_prediction_result(payload: dict[str, Any], include_ai_guidance: bool = False) -> dict[str, str]:
    scaler, model, defaults = get_model_bundle()

    features = defaults.copy()
    for key in FEATURE_COLUMNS:
        value = payload.get(key)
        try:
            if value is not None and value != "":
                features[key] = float(value)
        except (TypeError, ValueError):
            continue

    input_df = pd.DataFrame([[features[col] for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
    probability = float(model.predict_proba(scaler.transform(input_df))[0][1])
    prediction_class = 1 if probability >= PREDICTION_THRESHOLD else 0
    probability_pct = max(0.0, min(probability * 100.0, 100.0))
    dashoffset = 503.0 * (1.0 - (probability_pct / 100.0))

    risk_text = "High Risk Level" if prediction_class == 1 else "Low Risk Level"
    risk_badge_classes = (
        "bg-error-container/40 text-error border border-error/30"
        if prediction_class == 1
        else "bg-tertiary-container/20 text-on-tertiary border border-tertiary/20"
    )

    directives = _normalize_directives(None)
    physician_note = DEFAULT_PHYSICIAN_NOTE
    if include_ai_guidance:
        directives, physician_note = _fetch_gemini_directives(payload, probability_pct, risk_text)

    return {
        "probability_text": f"{probability_pct:.1f}%",
        "prediction_text": f"Prediction: {risk_text}",
        "risk_level_text": "ELEVATED" if prediction_class == 1 else "LOW RISK",
        "risk_badge_classes": risk_badge_classes,
        "stroke_dashoffset": f"{dashoffset:.2f}",
        "vascular_index": f"{max(1, min(round(100 - probability_pct), 99))}",
        "metabolic_bpm": f"{max(45, min(round(features['heartRate']), 130))}",
        "directive_1_title": directives[0]["title"],
        "directive_1_detail": directives[0]["detail"],
        "directive_2_title": directives[1]["title"],
        "directive_2_detail": directives[1]["detail"],
        "directive_3_title": directives[2]["title"],
        "directive_3_detail": directives[2]["detail"],
        "physician_note": physician_note,
        "user_inputs": payload,
        "age": f"{int(features['age'])}",
        "sys_bp": f"{int(features['sysBP'])}",
        "dia_bp": f"{int(features['diaBP'])}",
        "bmi": f"{features['BMI']:.1f}",
        "heart_rate": f"{int(features['heartRate'])}",
    }


def file_to_blob_url(
    file_path: Path,
    prediction_result: dict[str, str] | None = None,
    prefill_payload: dict[str, Any] | None = None,
    page_key: str = "",
    show_shimmer: bool = False,
) -> str:
    html = file_path.read_text(encoding="utf-8")
    dashboard_defaults = {
        "probability_text": "14.2%",
        "prediction_text": "Prediction: Low Risk Level",
        "risk_level_text": "LOW RISK",
        "risk_badge_classes": "bg-tertiary-container/20 text-on-tertiary border border-tertiary/20",
        "stroke_dashoffset": "431.57",
        "vascular_index": "88",
        "metabolic_bpm": "62",
        "directive_1_title": DEFAULT_DIRECTIVES[0]["title"],
        "directive_1_detail": DEFAULT_DIRECTIVES[0]["detail"],
        "directive_2_title": DEFAULT_DIRECTIVES[1]["title"],
        "directive_2_detail": DEFAULT_DIRECTIVES[1]["detail"],
        "directive_3_title": DEFAULT_DIRECTIVES[2]["title"],
        "directive_3_detail": DEFAULT_DIRECTIVES[2]["detail"],
        "physician_note": DEFAULT_PHYSICIAN_NOTE,
        "age": "45",
        "sys_bp": "120",
        "dia_bp": "80",
        "bmi": "25.0",
        "heart_rate": "72",
    }
    dashboard_values = prediction_result if prediction_result else dashboard_defaults

    html = html.replace("{{PROBABILITY_TEXT}}", dashboard_values["probability_text"])
    html = html.replace("{{PREDICTION_TEXT}}", dashboard_values["prediction_text"])
    html = html.replace("{{RISK_LEVEL_TEXT}}", dashboard_values["risk_level_text"])
    html = html.replace("{{RISK_BADGE_CLASSES}}", dashboard_values["risk_badge_classes"])
    html = html.replace("{{STROKE_DASHOFFSET}}", dashboard_values["stroke_dashoffset"])
    html = html.replace("{{VASCULAR_INDEX}}", dashboard_values["vascular_index"])
    html = html.replace("{{METABOLIC_BPM}}", dashboard_values["metabolic_bpm"])
    html = html.replace("{{DIRECTIVE_1_TITLE}}", dashboard_values["directive_1_title"])
    html = html.replace("{{DIRECTIVE_1_DETAIL}}", dashboard_values["directive_1_detail"])
    html = html.replace("{{DIRECTIVE_2_TITLE}}", dashboard_values["directive_2_title"])
    html = html.replace("{{DIRECTIVE_2_DETAIL}}", dashboard_values["directive_2_detail"])
    html = html.replace("{{DIRECTIVE_3_TITLE}}", dashboard_values["directive_3_title"])
    html = html.replace("{{DIRECTIVE_3_DETAIL}}", dashboard_values["directive_3_detail"])
    html = html.replace("{{PHYSICIAN_NOTE}}", dashboard_values["physician_note"])
    html = html.replace("{{AGE}}", dashboard_values["age"])
    html = html.replace("{{SYS_BP}}", dashboard_values["sys_bp"])
    html = html.replace("{{DIA_BP}}", dashboard_values["dia_bp"])
    html = html.replace("{{BMI}}", dashboard_values["bmi"])
    html = html.replace("{{HEART_RATE}}", dashboard_values["heart_rate"])

    user_data_html = '<div class="grid grid-cols-5 gap-y-3 gap-x-2 w-full">'
    if "user_inputs" in dashboard_values and dashboard_values["user_inputs"]:
        labels_map = {
          "male": "Sex", "age": "Age", "currentSmoker": "Smoker", "cigsPerDay": "Cigs/Day",
          "BPMeds": "BP Meds", "prevalentStroke": "Stroke History", "prevalentHyp": "Hypertension",
          "diabetes": "Diabetes", "totChol": "Cholesterol", "sysBP": "Sys BP", "diaBP": "Dia BP",
          "BMI": "BMI", "heartRate": "Heart Rate", "glucose": "Glucose"
        }
        for k, v in dashboard_values["user_inputs"].items():
            if k in labels_map:
                v_str = str(v)
                if k == "male": v_str = "Male" if v_str == "1" else "Female"
                elif k in ["currentSmoker", "BPMeds", "prevalentStroke", "prevalentHyp", "diabetes"]:
                    v_str = "Yes" if v_str == "1" else "No"
                # Removed the boxes, optimized font sizes, and moved to 5 columns to prevent overflow
                user_data_html += f'<div class="flex flex-col"><p class="text-[9px] text-slate-500 font-bold uppercase tracking-wider mb-0.5">{labels_map[k]}</p><p class="text-slate-900 font-bold text-[13px] tracking-wide">{v_str}</p></div>'
    user_data_html += '</div>'

    html = html.replace("{{PATIENT_DATA_GRID}}", user_data_html)

    fit_css = (
        "<style>"
        "html, body { margin: 0 !important; padding: 0 !important; width: 100% !important; max-width: 100% !important; overflow-x: hidden !important; background-color: #0e1322 !important; }"
        "body { opacity: 0; transition: opacity 0.12s ease-out; }"
        "body.ce-ready { opacity: 1; }"
        "* { box-sizing: border-box; }"
        "@keyframes ceShimmer{0%{background-position:100% 0}100%{background-position:-100% 0}}"
        ".ce-page-loader{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;padding:24px;background:#0e1322;opacity:1;transition:opacity 0.28s ease}"
        ".ce-page-loader.is-hidden{opacity:0;pointer-events:none}"
        ".ce-shimmer{border-radius:12px;background:linear-gradient(90deg,rgba(148,163,184,.12),rgba(148,163,184,.28),rgba(148,163,184,.12));background-size:200% 100%;animation:ceShimmer 1.1s linear infinite}"
        "</style>"
        "<script>"
        "(function() {"
        "  var revealed = false;"
        "  function reveal() {"
        "    if (revealed || !document.body) return;"
        "    revealed = true;"
        "    requestAnimationFrame(function() {"
        "      requestAnimationFrame(function() {"
        "        document.body.classList.add('ce-ready');"
        "      });"
        "    });"
        "  }"
        "  function onLoaded() {"
        "    if (document.fonts && document.fonts.ready) {"
        "      Promise.race(["
        "        document.fonts.ready,"
        "        new Promise(function(resolve) { setTimeout(resolve, 180); })"
        "      ]).then(reveal);"
        "      return;"
        "    }"
        "    reveal();"
        "  }"
        "  if (document.readyState === 'complete') {"
        "    onLoaded();"
        "  } else {"
        "    window.addEventListener('load', onLoaded, { once: true });"
        "    setTimeout(reveal, 260);"
        "  }"
        "})();"
        "</script>"
    )

    if "</head>" in html:
        html = html.replace("</head>", f"{fit_css}</head>", 1)
    else:
        html = fit_css + html

    tailwind_suppress = (
        "<script>"
        "const _origWarn = console.warn;"
        "console.warn = function() {"
        "  if (arguments[0] && typeof arguments[0] === 'string' && arguments[0].includes('cdn.tailwindcss')) return;"
        "  _origWarn.apply(console, arguments);"
        "};"
        "</script>"
    )
    if "<head>" in html:
        html = html.replace("<head>", f"<head>{tailwind_suppress}", 1)

    if show_shimmer:
        shimmer_html = (
            '<div class="ce-page-loader" id="cePageLoader" style="position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;padding:24px;background:#0e1322;opacity:1">' +
            '<div class="relative w-full max-w-6xl rounded-3xl overflow-hidden border border-white/15 bg-gradient-to-br from-white/10 to-white/5">' +
            '<button class="absolute top-4 right-4 z-[110] p-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 transition-all active:scale-90 group" onclick="window.parent.postMessage({type:\'navigate\',page:\'prediction_dashboard\',preservePredictPayload:true},\'*\')">' +
            '<span class="material-symbols-outlined text-on-surface group-hover:text-primary">close</span>' +
            '</button>' +
            '<div class="flex min-h-[74vh]">' +
            '<div class="w-[60%] p-6 bg-gradient-to-b from-slate-900/50 to-slate-800/25">' +
            '<div class="ce-shimmer h-4 w-44 rounded-full"></div>' +
            '<div class="ce-shimmer h-9 w-80 mt-4"></div>' +
            '<div class="ce-shimmer h-4 w-52 mt-3"></div>' +
            '<div class="flex justify-center items-center h-[300px]">' +
            '<div class="ce-shimmer h-48 w-48 rounded-full"></div>' +
            '</div>' +
            '</div>' +
            '<div class="w-[40%] p-6 bg-black/35 border-l border-white/10">' +
            '<div class="ce-shimmer h-7 w-56"></div>' +
            '<div class="ce-shimmer h-20 w-full mt-5"></div>' +
            '<div class="ce-shimmer h-20 w-full mt-4"></div>' +
            '<div class="ce-shimmer h-20 w-full mt-4"></div>' +
            '<div class="ce-shimmer h-32 w-full mt-5"></div>' +
            '</div>' +
            '</div>' +
            '<div class="px-6 py-4 bg-black/45 border-t border-white/10 flex justify-between gap-4">' +
            '<div class="ce-shimmer h-4 w-52"></div>' +
            '<div class="flex gap-3">' +
            '<div class="ce-shimmer h-10 w-32 rounded-full"></div>' +
            '<div class="ce-shimmer h-10 w-32 rounded-full"></div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>'
        )

        if "<body" in html:
            body_pos = html.find("<body")
            body_end = html.find(">", body_pos) + 1
            html = html[:body_end] + shimmer_html + html[body_end:]
        elif "<BODY" in html:
            body_pos = html.find("<BODY")
            body_end = html.find(">", body_pos) + 1
            html = html[:body_end] + shimmer_html + html[body_end:]
        else:
            html = shimmer_html + html

    prefill_payload_json = json.dumps(prefill_payload if prefill_payload else {})

    nav_js = (
        "<script>"
        "document.addEventListener('click', function(e) {"
        "  var el = e.target.closest('[data-nav]');"
        "  if (!el) return;"
        "  e.preventDefault();"
        "  window.parent.postMessage({type:'navigate',page:el.getAttribute('data-nav')}, '*');"
        "});"
        "document.addEventListener('DOMContentLoaded', function() {"
        "  var btn = document.querySelector('[data-action=\"run-analysis\"]');"
        "  if (!btn) return;"
        "  var pendingTimer = null;"
        "  var messageEl = document.querySelector('[data-validation-message]');"
        "  var prefillPayload = __PREFILL_PAYLOAD__;"
        "  var currentSmokerInput = document.querySelector('[data-field=\"currentSmoker\"]');"
        "  var cigsPerDayInput = document.querySelector('[data-field=\"cigsPerDay\"]');"
        "  function applyPrefill() {"
        "    if (!prefillPayload || typeof prefillPayload !== 'object') return;"
        "    Object.keys(prefillPayload).forEach(function(name) {"
        "      var input = document.querySelector('[data-field=\"' + name + '\"]');"
        "      if (!input) return;"
        "      var value = prefillPayload[name];"
        "      if (value === null || value === undefined || value === '') return;"
        "      input.value = String(value);"
        "    });"
        "  }"
        "  function clearFieldWarning(input) {"
        "    if (!input) return;"
        "    input.style.boxShadow = '';"
        "    input.style.border = '';"
        "    input.removeAttribute('title');"
        "    if (input.tagName === 'INPUT' && input.dataset.originalPlaceholder !== undefined) {"
        "      input.placeholder = input.dataset.originalPlaceholder;"
        "    }"
        "  }"
        "  function markFieldWarning(input, label) {"
        "    if (!input) return;"
        "    input.style.boxShadow = '0 0 0 2px rgba(248, 113, 113, 0.75)';"
        "    input.style.border = '1px solid rgba(248, 113, 113, 0.55)';"
        "    input.title = label + ' is required';"
        "    if (input.tagName === 'INPUT') {"
        "      if (input.dataset.originalPlaceholder === undefined) {"
        "        input.dataset.originalPlaceholder = input.placeholder || '';"
        "      }"
        "      input.placeholder = label + ' is required';"
        "    }"
        "  }"
        "  function setButtonPending(isPending) {"
        "    btn.disabled = !!isPending;"
        "    btn.classList.toggle('opacity-70', !!isPending);"
        "    if (!isPending && pendingTimer) {"
        "      clearTimeout(pendingTimer);"
        "      pendingTimer = null;"
        "    }"
        "  }"
        "  function syncSmokerDependency() {"
        "    if (!currentSmokerInput || !cigsPerDayInput) return;"
        "    var smokerValue = String(currentSmokerInput.value || '').trim();"
        "    var isNonSmoker = smokerValue === '0';"
        "    cigsPerDayInput.disabled = isNonSmoker;"
        "    cigsPerDayInput.classList.toggle('opacity-60', isNonSmoker);"
        "    cigsPerDayInput.classList.toggle('cursor-not-allowed', isNonSmoker);"
        "    if (isNonSmoker) {"
        "      cigsPerDayInput.value = '0';"
        "      clearFieldWarning(cigsPerDayInput);"
        "    }"
        "  }"
        "  if (currentSmokerInput) {"
        "    currentSmokerInput.addEventListener('change', syncSmokerDependency);"
        "  }"
        "  setButtonPending(false);"
        "  applyPrefill();"
        "  syncSmokerDependency();"
        "  btn.addEventListener('click', function(e) {"
        "    e.preventDefault();"
        "    var fields = ["
        "      'male','age','currentSmoker','cigsPerDay','BPMeds','prevalentStroke','prevalentHyp',"
        "      'diabetes','totChol','sysBP','diaBP','BMI','heartRate','glucose'"
        "    ];"
        "    var labels = {"
        "      male:'Sex', age:'Patient Age', currentSmoker:'Current Smoker', cigsPerDay:'Cigarettes / Day',"
        "      BPMeds:'BP Medication', prevalentStroke:'Prevalent Stroke', prevalentHyp:'Prevalent Hypertension',"
        "      diabetes:'Diabetes', totChol:'Total Cholesterol', sysBP:'Systolic Blood Pressure', diaBP:'Diastolic Blood Pressure',"
        "      BMI:'BMI', heartRate:'Heart Rate', glucose:'Glucose'"
        "    };"
        "    var payload = {};"
        "    var missing = [];"
        "    var smokerValue = currentSmokerInput ? String(currentSmokerInput.value || '').trim() : '';"
        "    fields.forEach(function(name) {"
        "      var input = document.querySelector('[data-field=\"' + name + '\"]');"
        "      if (name === 'cigsPerDay' && smokerValue === '0') {"
        "        payload[name] = '0';"
        "        clearFieldWarning(input);"
        "        return;"
        "      }"
        "      var val = input ? String(input.value || '').trim() : '';"
        "      payload[name] = val;"
        "      if (!val) {"
        "        missing.push(labels[name] || name);"
        "        markFieldWarning(input, labels[name] || name);"
        "      } else {"
        "        clearFieldWarning(input);"
        "      }"
        "    });"
        "    if (missing.length > 0) {"
        "      if (messageEl) {"
        "        messageEl.textContent = '';"
        "        messageEl.classList.add('hidden');"
        "      }"
        "      return;"
        "    }"
        "    if (messageEl) {"
        "      messageEl.textContent = '';"
        "      messageEl.classList.add('hidden');"
        "    }"
        "    setButtonPending(true);"
        "    window.parent.postMessage({type:'predict', payload: payload}, '*');"
        "  });"
        "});"
        "</script>"
    )
    nav_js = nav_js.replace("__PREFILL_PAYLOAD__", prefill_payload_json)

    if "</body>" in html:
        html = html.replace("</body>", f"{nav_js}</body>", 1)
    else:
        html = html + nav_js

    # Use blob URL for same-origin access
    blob = f"data:text/html;base64,{base64.b64encode(html.encode('utf-8')).decode('utf-8')}"
    return blob


def main() -> None:
    apply_chrome_cleanup()

    if not st.session_state.get("_nav_listener_injected", False):
        inject_nav_listener()
        st.session_state["_nav_listener_injected"] = True

    page_key = get_page_key()
    html_path = PAGE_TEMPLATE_MAP.get(page_key)

    if not html_path or not html_path.exists():
        st.error(f"Template not found: {html_path}")
        return

    iframe_placeholder = st.empty()

    if page_key == "result_page":
        # Show the shimmer UI first, waiting for the model execution
        blob = file_to_blob_url(
            html_path,
            prediction_result=None,
            prefill_payload=None,
            page_key=page_key,
            show_shimmer=True,
        )
        iframe_placeholder.markdown(f'<iframe class="ce-main-iframe" src="{blob}" style="width:100vw; height:100vh; border:none; margin:0; padding:0; display:block;"></iframe>', unsafe_allow_html=True)

        # Execute heavy backend process
        payload = parse_prediction_payload()
        prediction_result = None
        if payload:
            prediction_result = build_prediction_result(
                payload,
                include_ai_guidance=True,
            )

        # Overwrite shimmer with actual results
        blob = file_to_blob_url(
            html_path,
            prediction_result=prediction_result,
            prefill_payload=None,
            page_key=page_key,
            show_shimmer=False,
        )
        iframe_placeholder.markdown(f'<iframe class="ce-main-iframe" src="{blob}" style="width:100vw; height:100vh; border:none; margin:0; padding:0; display:block;"></iframe>', unsafe_allow_html=True)

    else:
        payload = None
        prediction_result = None
        if page_key == "prediction_dashboard":
            payload = parse_prediction_payload()
            if payload:
                prediction_result = build_prediction_result(
                    payload,
                    include_ai_guidance=False,
                )

        blob = file_to_blob_url(
            html_path,
            prediction_result=prediction_result,
            prefill_payload=payload if page_key == "prediction_dashboard" else None,
            page_key=page_key,
            show_shimmer=False,
        )
        iframe_placeholder.markdown(f'<iframe class="ce-main-iframe" src="{blob}" style="width:100vw; height:100vh; border:none; margin:0; padding:0; display:block;"></iframe>', unsafe_allow_html=True)

def inject_nav_listener() -> None:
    components.html(
        """
        <script>
        (function() {
            if (window.parent.__navListenerInjected) return;
            window.parent.__navListenerInjected = true;
            var s = window.parent.document.createElement('script');
            s.textContent = [
                '(function(){',
                '  if(window.__navListenerReady) return;',
                '  window.__navListenerReady = true;',
                '  window.addEventListener("message", function(e){',
                '    if (!e.data) return;',
                '    if (e.data.type==="navigate" && e.data.page) {',
                '      var u = new URL(window.location.href);',
                '      u.searchParams.set("page", e.data.page);',
                '      var keepPayload = e.data.page==="prediction_dashboard" && e.data.preservePredictPayload===true;',
                '      if (!keepPayload) {',
                '        u.searchParams.delete("predict_payload");',
                '        u.searchParams.delete("predict_ts");',
                '      }',
                '      setTimeout(function() { window.location.replace(u.toString()); }, 100);',
                '    }',
                '    if (e.data.type==="predict" && e.data.payload) {',
                '      var u = new URL(window.location.href);',
                '      u.searchParams.set("page", "result_page");',
                '      u.searchParams.set("predict_payload", btoa(JSON.stringify(e.data.payload)));',
                '      u.searchParams.set("predict_ts", Date.now().toString());',
                '      setTimeout(function() { window.location.replace(u.toString()); }, 100);',
                '    }',
                '  }, false);',
                '})()'
            ].join('');
            window.parent.document.head.appendChild(s);
        })();
        </script>
        """,
        height=1,
    )


if __name__ == "__main__":
    main()
