from __future__ import annotations

import streamlit as st

from app.state.session_state import (
    clear_professor_notice,
    get_current_professor_tool,
    get_professor_authoring_ai_assisted,
    get_professor_notice,
    set_current_professor_tool,
    set_professor_authoring_ai_assisted,
    set_professor_notice,
)
from modules.services.question_authoring_service import (
    AI_POLISHED_QUESTION_SOURCE,
    DIFFICULTY_LABEL_BY_VALUE,
    MANUAL_QUESTION_SOURCE,
    AuthoringAlternativeDraft,
    QuestionAuthoringDraft,
    QuestionAuthoringService,
    build_question_row_from_draft,
    format_difficulty_label,
    normalize_difficulty_value,
    validate_draft_for_ai,
    validate_draft_for_submission,
)
from modules.services.user_service import (
    build_student_access_row,
    has_active_project_access,
    parse_user_access_dataframe,
)
from modules.storage.bigquery_client import BigQueryError
from modules.storage.question_repository import QuestionRepository
from modules.storage.user_access_repository import UserAccessRepository
from modules.utils.normalization import clean_optional_text

PROFESSOR_TOOL_GENERATE_QUESTIONS = "generate_questions"
PROFESSOR_TOOL_ADD_STUDENT = "add_student"
AUTHORING_SUBJECT_KEY = "gm_prof_authoring_subject"
AUTHORING_TOPIC_KEY = "gm_prof_authoring_topic"
AUTHORING_DIFFICULTY_KEY = "gm_prof_authoring_difficulty"
AUTHORING_STATEMENT_KEY = "gm_prof_authoring_statement"
AUTHORING_CORRECT_TEXT_KEY = "gm_prof_authoring_correct_text"
AUTHORING_CORRECT_EXPLANATION_KEY = "gm_prof_authoring_correct_explanation"
AUTHORING_WRONG_TEXT_KEYS = (
    "gm_prof_authoring_wrong_text_1",
    "gm_prof_authoring_wrong_text_2",
    "gm_prof_authoring_wrong_text_3",
)
AUTHORING_WRONG_EXPLANATION_KEYS = (
    "gm_prof_authoring_wrong_explanation_1",
    "gm_prof_authoring_wrong_explanation_2",
    "gm_prof_authoring_wrong_explanation_3",
)
AUTHORING_PROJECT_SCOPE_KEY = "gm_prof_authoring_project_scope"
ADD_STUDENT_EMAIL_KEY = "gm_prof_add_student_email"


def render_professor_page(
    *,
    selected_project: str | None,
    question_repository: QuestionRepository,
    user_access_repository: UserAccessRepository,
    gemini_api_key: str | None,
    gemini_model: str,
) -> None:
    """Render the teacher/admin workspace."""

    _apply_professor_page_styles()
    _render_notice()
    _render_menu_cards()

    current_tool = get_current_professor_tool() or PROFESSOR_TOOL_GENERATE_QUESTIONS
    if current_tool not in {PROFESSOR_TOOL_GENERATE_QUESTIONS, PROFESSOR_TOOL_ADD_STUDENT}:
        set_current_professor_tool(PROFESSOR_TOOL_GENERATE_QUESTIONS)
        current_tool = PROFESSOR_TOOL_GENERATE_QUESTIONS

    if current_tool == PROFESSOR_TOOL_GENERATE_QUESTIONS:
        _render_question_authoring_panel(
            selected_project=selected_project,
            question_repository=question_repository,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
        )
    elif current_tool == PROFESSOR_TOOL_ADD_STUDENT:
        _render_add_student_panel(
            selected_project=selected_project,
            user_access_repository=user_access_repository,
        )


def _render_notice() -> None:
    notice = get_professor_notice()
    if notice is None:
        return

    kind = notice["kind"]
    message = notice["message"]
    if kind == "success":
        st.success(message)
    elif kind == "error":
        st.error(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.info(message)
    clear_professor_notice()


def _render_menu_cards() -> None:
    current_tool = get_current_professor_tool() or PROFESSOR_TOOL_GENERATE_QUESTIONS
    with st.container():
        st.html('<div class="gm-professor-menu-hook"></div>')
        first_col, second_col = st.columns(2, gap="small")

        with first_col:
            if st.button(
                "Gerar questões",
                key="gm_professor_tool_generate_questions",
                icon=":material/auto_awesome:",
                type="primary" if current_tool == PROFESSOR_TOOL_GENERATE_QUESTIONS else "secondary",
                use_container_width=True,
            ):
                if current_tool != PROFESSOR_TOOL_GENERATE_QUESTIONS:
                    set_current_professor_tool(PROFESSOR_TOOL_GENERATE_QUESTIONS)
                    st.rerun()

        with second_col:
            if st.button(
                "Adicionar aluno",
                key="gm_professor_tool_add_student",
                icon=":material/person_add:",
                type="primary" if current_tool == PROFESSOR_TOOL_ADD_STUDENT else "secondary",
                use_container_width=True,
            ):
                if current_tool != PROFESSOR_TOOL_ADD_STUDENT:
                    set_current_professor_tool(PROFESSOR_TOOL_ADD_STUDENT)
                    st.rerun()


def _render_question_authoring_panel(
    *,
    selected_project: str | None,
    question_repository: QuestionRepository,
    gemini_api_key: str | None,
    gemini_model: str,
) -> None:
    normalized_project = clean_optional_text(selected_project)
    if normalized_project is None:
        st.warning(
            "Selecione um projeto acima para liberar o gerador de questões."
        )
        return

    with st.container():
        st.html(
            """
            <section class="gm-professor-card">
              <div class="gm-professor-eyebrow">Espaço Professor</div>
              <h2 class="gm-professor-title">Gerar questões</h2>
              <p class="gm-professor-copy">
                Monte uma questão manualmente ou peça para a IA polir o rascunho antes de enviar.
              </p>
            </section>
            """
        )

    _ensure_authoring_project_scope(normalized_project)
    _ensure_authoring_widget_defaults()

    with st.form("gm_professor_question_authoring_form", clear_on_submit=False):
        subject_col, topic_col = st.columns(2, gap="small")
        with subject_col:
            st.text_input(
                "Matéria",
                key=AUTHORING_SUBJECT_KEY,
                placeholder="Ex.: Matemática, Certificação Databricks",
            )
        with topic_col:
            st.text_input(
                "Tópico",
                key=AUTHORING_TOPIC_KEY,
                placeholder="Ex.: divisão, Auto Loader, radiciação",
            )

        st.selectbox(
            "Dificuldade",
            options=list(DIFFICULTY_LABEL_BY_VALUE),
            index=None,
            format_func=format_difficulty_label,
            key=AUTHORING_DIFFICULTY_KEY,
            placeholder="Selecione a dificuldade",
        )

        st.text_area(
            "Enunciado",
            key=AUTHORING_STATEMENT_KEY,
            height=150,
            placeholder="Descreva o problema. Você pode usar Markdown e blocos de código.",
        )

        st.markdown("**Alternativa correta**")
        st.text_area(
            "Texto da alternativa correta",
            key=AUTHORING_CORRECT_TEXT_KEY,
            height=110,
            placeholder="Resposta correta.",
        )
        st.text_area(
            "Explicação da alternativa correta",
            key=AUTHORING_CORRECT_EXPLANATION_KEY,
            height=110,
            placeholder="Explique por que a alternativa correta está certa.",
        )

        for index in range(3):
            human_index = index + 1
            st.markdown(f"**Alternativa errada {human_index}**")
            st.text_area(
                f"Texto da alternativa errada {human_index}",
                key=AUTHORING_WRONG_TEXT_KEYS[index],
                height=110,
                placeholder="Resposta incorreta, mas plausível.",
            )
            st.text_area(
                f"Explicação da alternativa errada {human_index}",
                key=AUTHORING_WRONG_EXPLANATION_KEYS[index],
                height=110,
                placeholder="Explique por que esta alternativa está errada.",
            )

        polish_col, submit_col = st.columns(2, gap="small")
        with polish_col:
            polish_clicked = st.form_submit_button(
                "Polir com IA",
                use_container_width=True,
            )
        with submit_col:
            submit_clicked = st.form_submit_button(
                "Enviar para o banco",
                type="primary",
                use_container_width=True,
            )

    draft = _build_current_authoring_draft(project_key=normalized_project)

    if polish_clicked:
        _handle_polish_with_ai(
            draft=draft,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
        )

    if submit_clicked:
        _handle_submit_question(
            draft=draft,
            question_repository=question_repository,
        )


def _handle_polish_with_ai(
    *,
    draft: QuestionAuthoringDraft,
    gemini_api_key: str | None,
    gemini_model: str,
) -> None:
    issues = validate_draft_for_ai(draft)
    if issues:
        for issue in issues:
            st.warning(issue)
        return

    try:
        from modules.ai.gemini_client import (
            GeminiClient,
            GeminiConfigurationError,
            GeminiGenerationError,
        )

        authoring_service = QuestionAuthoringService(
            GeminiClient(
                api_key=gemini_api_key,
                model=gemini_model,
            )
        )
        polished_draft = authoring_service.polish_draft(draft)
    except ImportError:
        st.error(
            "A dependência do Gemini ainda não está instalada neste ambiente."
        )
        return
    except GeminiConfigurationError as exc:
        st.error(str(exc))
        return
    except GeminiGenerationError as exc:
        st.error(str(exc))
        return

    _apply_draft_to_widget_state(polished_draft)
    set_professor_authoring_ai_assisted(True)
    set_professor_notice(
        "success",
        "A IA preencheu o formulário. Revise os campos e envie quando estiver satisfeito.",
    )
    st.rerun()


def _handle_submit_question(
    *,
    draft: QuestionAuthoringDraft,
    question_repository: QuestionRepository,
) -> None:
    issues = validate_draft_for_submission(draft)
    if issues:
        for issue in issues:
            st.warning(issue)
        return

    source = (
        AI_POLISHED_QUESTION_SOURCE
        if get_professor_authoring_ai_assisted()
        else MANUAL_QUESTION_SOURCE
    )

    try:
        row = build_question_row_from_draft(draft, source=source)
        question_repository.append_question_row(row)
    except (BigQueryError, ValueError) as exc:
        st.error(str(exc))
        return

    _reset_authoring_form(
        project_key=draft.project_key,
        subject=draft.subject,
        topic=draft.topic,
        difficulty=draft.difficulty,
    )
    set_professor_notice(
        "success",
        f"Questão {row['id_question']} enviada com sucesso para o banco.",
    )
    st.rerun()


def _render_add_student_panel(
    *,
    selected_project: str | None,
    user_access_repository: UserAccessRepository,
) -> None:
    normalized_project = clean_optional_text(selected_project)
    if normalized_project is None:
        st.warning("Selecione um projeto acima para liberar o cadastro de alunos.")
        return

    st.session_state.setdefault(ADD_STUDENT_EMAIL_KEY, "")

    with st.container():
        st.html(
            """
            <section class="gm-professor-card">
              <div class="gm-professor-eyebrow">Espaço Professor</div>
              <h2 class="gm-professor-title">Adicionar aluno</h2>
              <p class="gm-professor-copy">
                Informe o e-mail do aluno para liberar acesso a este projeto.
              </p>
            </section>
            """
        )

    with st.form("gm_professor_add_student_form", clear_on_submit=False):
        st.text_input(
            "E-mail do aluno",
            key=ADD_STUDENT_EMAIL_KEY,
            placeholder="aluno@exemplo.com",
        )
        submitted = st.form_submit_button(
            "Adicionar aluno",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        _handle_add_student(
            email=clean_optional_text(st.session_state.get(ADD_STUDENT_EMAIL_KEY)),
            project_key=normalized_project,
            user_access_repository=user_access_repository,
        )


def _handle_add_student(
    *,
    email: str | None,
    project_key: str,
    user_access_repository: UserAccessRepository,
) -> None:
    try:
        existing_access_frame = user_access_repository.load_active_user_frame(email or "")
        existing_access_entries, issues = parse_user_access_dataframe(existing_access_frame)
        if issues:
            raise ValueError("Nao foi possivel validar os acessos atuais desse e-mail.")

        if has_active_project_access(existing_access_entries, cohort_key=project_key):
            set_professor_notice(
                "warning",
                "Esse e-mail já possui acesso ativo a este projeto.",
            )
            st.rerun()

        user_access_repository.append_access_row(
            build_student_access_row(
                email,
                cohort_key=project_key,
            )
        )
    except (BigQueryError, ValueError) as exc:
        st.error(str(exc))
        return

    st.session_state[ADD_STUDENT_EMAIL_KEY] = ""
    set_professor_notice(
        "success",
        f"Acesso liberado para {email} neste projeto.",
    )
    st.rerun()


def _build_current_authoring_draft(*, project_key: str | None) -> QuestionAuthoringDraft:
    wrong_answers = tuple(
        AuthoringAlternativeDraft(
            alternative_text=clean_optional_text(st.session_state.get(text_key)),
            explanation=clean_optional_text(st.session_state.get(explanation_key)),
        )
        for text_key, explanation_key in zip(
            AUTHORING_WRONG_TEXT_KEYS,
            AUTHORING_WRONG_EXPLANATION_KEYS,
            strict=True,
        )
    )
    return QuestionAuthoringDraft(
        project_key=clean_optional_text(project_key),
        subject=clean_optional_text(st.session_state.get(AUTHORING_SUBJECT_KEY)),
        topic=clean_optional_text(st.session_state.get(AUTHORING_TOPIC_KEY)),
        difficulty=normalize_difficulty_value(
            clean_optional_text(st.session_state.get(AUTHORING_DIFFICULTY_KEY))
        ),
        statement=clean_optional_text(st.session_state.get(AUTHORING_STATEMENT_KEY)),
        correct_answer=AuthoringAlternativeDraft(
            alternative_text=clean_optional_text(st.session_state.get(AUTHORING_CORRECT_TEXT_KEY)),
            explanation=clean_optional_text(st.session_state.get(AUTHORING_CORRECT_EXPLANATION_KEY)),
        ),
        wrong_answers=wrong_answers,
    )


def _apply_draft_to_widget_state(draft: QuestionAuthoringDraft) -> None:
    st.session_state[AUTHORING_SUBJECT_KEY] = draft.subject or ""
    st.session_state[AUTHORING_TOPIC_KEY] = draft.topic or ""
    st.session_state[AUTHORING_DIFFICULTY_KEY] = normalize_difficulty_value(draft.difficulty)
    st.session_state[AUTHORING_STATEMENT_KEY] = draft.statement or ""
    st.session_state[AUTHORING_CORRECT_TEXT_KEY] = draft.correct_answer.alternative_text or ""
    st.session_state[AUTHORING_CORRECT_EXPLANATION_KEY] = draft.correct_answer.explanation or ""
    for index, wrong_answer in enumerate(draft.wrong_answers):
        st.session_state[AUTHORING_WRONG_TEXT_KEYS[index]] = wrong_answer.alternative_text or ""
        st.session_state[AUTHORING_WRONG_EXPLANATION_KEYS[index]] = wrong_answer.explanation or ""


def _reset_authoring_form(
    *,
    project_key: str | None,
    subject: str | None,
    topic: str | None,
    difficulty: str | None,
) -> None:
    _apply_draft_to_widget_state(
        QuestionAuthoringDraft(
            project_key=project_key,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
        )
    )
    set_professor_authoring_ai_assisted(False)


def _ensure_authoring_widget_defaults() -> None:
    st.session_state.setdefault(AUTHORING_SUBJECT_KEY, "")
    st.session_state.setdefault(AUTHORING_TOPIC_KEY, "")
    st.session_state.setdefault(AUTHORING_DIFFICULTY_KEY, None)
    st.session_state.setdefault(AUTHORING_STATEMENT_KEY, "")
    st.session_state.setdefault(AUTHORING_CORRECT_TEXT_KEY, "")
    st.session_state.setdefault(AUTHORING_CORRECT_EXPLANATION_KEY, "")
    for key in AUTHORING_WRONG_TEXT_KEYS + AUTHORING_WRONG_EXPLANATION_KEYS:
        st.session_state.setdefault(key, "")


def _ensure_authoring_project_scope(project_key: str) -> None:
    current_scope = clean_optional_text(st.session_state.get(AUTHORING_PROJECT_SCOPE_KEY))
    if current_scope == project_key:
        return

    _reset_authoring_form(
        project_key=project_key,
        subject=None,
        topic=None,
        difficulty=None,
    )
    st.session_state[AUTHORING_PROJECT_SCOPE_KEY] = project_key


def _apply_professor_page_styles() -> None:
    st.html(
        """
        <style>
        .gm-professor-card {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 1.35rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            margin: 0;
            padding: 1.1rem 1.1rem 1rem;
        }

        .gm-professor-eyebrow {
            color: #475569;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 0.34rem;
            text-transform: uppercase;
        }

        .gm-professor-title {
            color: #0f172a;
            font-size: 1.52rem;
            font-weight: 800;
            line-height: 1.08;
            margin: 0 0 0.45rem;
        }

        .gm-professor-copy {
            color: #475569;
            font-size: 1.04rem;
            line-height: 1.52;
            margin: 0;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-professor-menu-hook) div[data-testid="stButton"] > button {
            align-items: center;
            border-radius: 1.4rem !important;
            display: flex;
            flex-direction: column;
            font-size: 1.2rem !important;
            font-weight: 800 !important;
            gap: 0.45rem;
            justify-content: center;
            min-height: 9.5rem !important;
            padding: 1rem 0.9rem !important;
            text-align: center;
            white-space: normal !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-professor-menu-hook) div[data-testid="stButton"] > button span[data-testid="stIconMaterial"] {
            font-size: 2.55rem !important;
        }

        div[data-testid="stVerticalBlock"]:has(.gm-professor-menu-hook) div[data-testid="stButton"] > button:disabled {
            background: #f8fafc !important;
            border-color: #e2e8f0 !important;
            color: #94a3b8 !important;
            opacity: 1 !important;
        }

        div[data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        div[data-testid="stForm"] form {
            background: #ffffff !important;
            border: 1px solid #dbeafe !important;
            border-radius: 1.35rem !important;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08) !important;
            padding: 1.05rem !important;
        }

        div[data-testid="stForm"] form > div[data-testid="stVerticalBlock"] {
            gap: 0.88rem !important;
        }

        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] label span {
            color: #334155 !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
        }

        div[data-testid="stForm"] [data-testid="InputInstructions"] {
            display: none !important;
        }

        div[data-testid="stForm"] textarea,
        div[data-testid="stForm"] input {
            border-radius: 1rem !important;
            font-size: 1rem !important;
        }

        div[data-testid="stForm"] [data-baseweb="base-input"],
        div[data-testid="stForm"] [data-baseweb="textarea"] {
            border-radius: 1rem !important;
        }

        div[data-testid="stForm"] input::placeholder,
        div[data-testid="stForm"] textarea::placeholder {
            color: #94a3b8 !important;
            font-size: 0.98rem !important;
        }

        div[data-testid="stForm"] [data-baseweb="select"] span {
            font-size: 1rem !important;
        }

        div[data-testid="stForm"] [data-testid="stMarkdownContainer"] p {
            color: #0f172a !important;
            font-size: 1.02rem !important;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button {
            background: #edf4ff !important;
            border: 1px solid #93c5fd !important;
            border-radius: 1.12rem !important;
            box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12) !important;
            color: #1d4ed8 !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button:hover {
            background: #e2eeff !important;
            border-color: #60a5fa !important;
            color: #1d4ed8 !important;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #1e40af !important;
            border-color: #1e3a8a !important;
            box-shadow: 0 16px 30px rgba(30, 64, 175, 0.2) !important;
            color: #ffffff !important;
        }

        div[data-testid="stForm"] div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        </style>
        """
    )
