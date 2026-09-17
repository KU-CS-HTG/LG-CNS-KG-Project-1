"""webapp.py — 진로 추천 웹 페이지 (담당: D)

app.py 의 기본 흐름(플래그 없는 python app.py)과 같은 인터뷰를 웹으로 옮긴 것.
interview.InterviewSession 으로 user_analysis/main.py 와 같은 적응형 질문을 한 걸음씩 진행하고,
끝나면 app.run() → app.explain_stream() 으로 전공·과목·직무를 찾고 [진로 추천] 문단을 스트리밍한다.
판정(어떤 전공·직무를 추천할지)은 여기서 하지 않는다 — 전부 graph_store.py 몫이다.

화면에는 [핵심 요약](전공 순위·근거 과목·직무 커버리지 카드)이 바로 보인다. LLM이 쓰는 [진로 추천]
문단은 시간이 좀 더 걸리므로 "세부내용 확인" 링크를 눌러야 나오는 별도 페이지(/details/<result_id>)로 뺐다.
"""
from __future__ import annotations

import json
import secrets
import uuid

from flask import Flask, Response, abort, jsonify, render_template, request

from app import FOLLOWUP_PREFIX, explain_stream, render, run
from interview import INTRO_PROMPT, InterviewSession

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)   # 서버 재시작 시 기존 세션은 무효화된다 — 데모 규모라 문제 없음

# interview_id → 진행 중인 인터뷰 상태, result_id → 완료된 run() 결과.
# 둘 다 세션 쿠키엔 못 담을 만큼 크거나(InterviewSession, 전공 전수 순위) 재구성이 번거로워서 서버 메모리에 둔다.
# 단일 프로세스 데모 전제 — 여러 워커로 띄우면 워커마다 따로 논다.
_INTERVIEWS: dict[str, dict] = {}
_RESULTS: dict[str, dict] = {}


@app.get("/")
def index():
    return render_template("index.html", intro_prompt=INTRO_PROMPT)


def _summary_fields(result: dict) -> dict:
    """[핵심 요약]에 바로 보여줄 것 — render() 카드 + 근거 줄. LLM 호출 없음(render()는 순수 카드 헬퍼)."""
    evidence_lines = []
    if result.get("interest_evidence"):
        evidence_lines.append("관심·성향에서 읽은 역량: " +
                               "; ".join(f"{s} ← {e}" for s, e in result["interest_evidence"].items()))
    if result.get("trait_evidence"):
        evidence_lines.append("강점 성향에서 추정한 역량: " +
                               "; ".join(f"{s} ← {e}" for s, e in result["trait_evidence"].items()))
    return {"profile_text": render(result), "evidence_lines": evidence_lines}


def _store_result(result: dict, iv: dict) -> str:
    result_id = uuid.uuid4().hex
    _RESULTS[result_id] = {**result, "interest_evidence": iv["interest_evidence"], "trait_evidence": iv["trait_evidence"]}
    return result_id


def _finalize(state: dict) -> dict:
    """인터뷰(질문 루프)가 끝났다 — run() 을 돌려서 프론트에 줄 JSON payload를 만든다.

    run() 이 followup 을 요구하면 그 자체를 "질문 하나 더"로 취급해 같은 채팅 UI에서 잇는다
    (app.py CLI가 Q1 을 한 번 더 묻는 것과 같은 동작).
    """
    iv = state["interview"].finish()
    kw = dict(trait_tags=iv["trait_tags"], stated_tags=iv["interest_tags"],
              soft_traits=iv["soft_traits"], profile_summary=iv.get("profile_summary"))
    answers = iv["answers"] + [""]   # answers[2] 자리는 normalize_to_tags() 가 "Q3 자리"로 취급 — 빈 문자열로 맡아둔다
    result = run(answers, state["run_state"], **kw)

    if "followup" in result:
        state.update(stage="followup", pending_answers=answers, kw=kw, iv=iv)
        return {"status": "question", "question": FOLLOWUP_PREFIX + result["followup"]}

    state["stage"] = "done"
    if result.get("empty"):
        return {"status": "empty"}

    result_id = _store_result(result, iv)
    return {"status": "done", "result_id": result_id, **_summary_fields(_RESULTS[result_id])}


def _finish_followup(state: dict, answer: str) -> dict:
    answers = state["pending_answers"] + [answer]
    result = run(answers, state["run_state"], **state["kw"])
    state["stage"] = "done"
    if result.get("empty"):
        return {"status": "empty"}

    result_id = _store_result(result, state["iv"])
    return {"status": "done", "result_id": result_id, **_summary_fields(_RESULTS[result_id])}


@app.post("/api/interview/answer")
def interview_answer():
    body = request.get_json(silent=True) or {}
    answer = (body.get("answer") or "").strip()
    interview_id = body.get("interview_id")
    if not answer:
        return jsonify(error="답을 입력해 주세요."), 400

    if not interview_id:
        # 인터뷰 첫 답 = 자기소개. 여기서 새 세션을 만든다.
        sess = InterviewSession()
        q = sess.start(answer)
        interview_id = uuid.uuid4().hex
        state = {"interview": sess, "run_state": {}, "stage": "interview"}
        _INTERVIEWS[interview_id] = state
    else:
        state = _INTERVIEWS.get(interview_id)
        if state is None:
            return jsonify(error="세션을 찾을 수 없습니다. 새로고침 후 다시 시작해 주세요."), 404
        if state["stage"] == "followup":
            payload = _finish_followup(state, answer)
            return jsonify(interview_id=interview_id, **payload)
        if state["stage"] == "done":
            return jsonify(error="이미 끝난 인터뷰입니다. 새로고침 후 다시 시작해 주세요."), 400
        q = state["interview"].answer(answer)

    if q is not None:
        return jsonify(interview_id=interview_id, status="question", question=q)

    payload = _finalize(state)
    return jsonify(interview_id=interview_id, **payload)


@app.get("/api/explain/<result_id>")
def explain_endpoint(result_id: str):
    """[진로 추천] 문단을 Server-Sent Events 로 스트리밍."""
    result = _RESULTS.get(result_id)
    if result is None:
        return jsonify(error="결과를 찾을 수 없습니다. 처음부터 다시 시도해 주세요."), 404

    def event_stream():
        for chunk in explain_stream(result):
            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.get("/details/<result_id>")
def details(result_id: str):
    """[진로 추천] 문단 — [핵심 요약]과 달리 LLM이 쓰므로 시간이 걸린다. 이 링크를 눌러야 스트리밍이 시작된다."""
    if result_id not in _RESULTS:
        abort(404, description="결과를 찾을 수 없습니다. 처음부터 다시 시도해 주세요.")
    return render_template("details.html", result_id=result_id)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
