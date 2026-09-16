"""webapp.py — 진로 추천 웹 페이지 (담당: D)

app.py 의 run() / render() / explain_stream() 을 그대로 호출하는 Flask 서버.
질문에 답 → 전공·과목·직무를 찾고 → LLM이 쓴 [진로 추천] 문단을 화면에 스트리밍한다.
판정(어떤 전공·직무를 추천할지)은 여기서 하지 않는다 — 전부 graph_store.py 몫이다.
"""
from __future__ import annotations

import json
import secrets
import uuid

from flask import Flask, Response, jsonify, render_template, request, session

from app import QUESTIONS, explain_stream, render, run

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)   # 서버 재시작 시 기존 세션은 무효화된다 — 데모 규모라 문제 없음

# result_id → run() 의 전체 결과. 세션 쿠키엔 못 담을 만큼 크므로(전공 전수 순위 포함) 서버 메모리에 둔다.
# 단일 프로세스 데모 전제 — 여러 워커로 띄우면 워커마다 따로 논다.
_RESULTS: dict[str, dict] = {}


@app.get("/")
def index():
    return render_template("index.html", questions=QUESTIONS)


@app.post("/api/submit")
def submit():
    body = request.get_json(silent=True) or {}
    answers = body.get("answers")
    if not isinstance(answers, list) or len(answers) < len(QUESTIONS) or not all(a.strip() for a in answers):
        return jsonify(error="모든 질문에 답해 주세요."), 400

    state = session.get("state", {})
    result = run(answers, state)
    session["state"] = state   # run() 이 state 딕셔너리를 제자리에서 수정한다 (asked_again, tags)

    if "followup" in result:
        return jsonify(status="followup", question=result["followup"])

    if result.get("empty"):
        return jsonify(status="empty")

    result_id = uuid.uuid4().hex
    _RESULTS[result_id] = result

    return jsonify(
        status="done",
        result_id=result_id,
        profile_text=render(result),   # 전공 순위 · 근거 과목 · 직무 커버리지 요약 (app.py 재사용)
    )


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
