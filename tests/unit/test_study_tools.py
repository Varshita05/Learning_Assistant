import pytest

from learning_assistant import study_tools


def test_make_quiz_validates_backend_item_schema(monkeypatch):
    monkeypatch.setattr(study_tools, "_context", lambda topic: ("evidence", []))
    monkeypatch.setattr(
        study_tools,
        "complete",
        lambda *args, **kwargs: '[{"q":"Q?","options":["A","B","C","D"],"answer_index":2,"explain":"Because."}]',
    )

    result = study_tools.make_quiz("topic")

    assert result["items"][0]["q"] == "Q?"
    assert result["items"][0]["answer_index"] == 2


def test_make_quiz_rejects_invalid_answer_index(monkeypatch):
    monkeypatch.setattr(study_tools, "_context", lambda topic: ("evidence", []))
    monkeypatch.setattr(
        study_tools,
        "complete",
        lambda *args, **kwargs: '[{"q":"Q?","options":["A","B","C","D"],"answer_index":4,"explain":"Because."}]',
    )

    with pytest.raises(ValueError, match="invalid items"):
        study_tools.make_quiz("topic")


def test_make_flashcards_validates_backend_item_schema(monkeypatch):
    monkeypatch.setattr(study_tools, "_context", lambda topic: ("evidence", []))
    monkeypatch.setattr(
        study_tools,
        "complete",
        lambda *args, **kwargs: '[{"front":"Prompt","back":"Answer"}]',
    )

    result = study_tools.make_flashcards("topic")

    assert result["items"] == [{"front": "Prompt", "back": "Answer"}]


def test_study_prompts_exclude_front_matter_and_require_useful_evidence(monkeypatch):
    prompts = []
    monkeypatch.setattr(
        study_tools,
        "_context",
        lambda topic: ("SOURCE: notes.pdf (page 2)\nHEADING: Neural Networks\nEvidence text", []),
    )
    monkeypatch.setattr(
        study_tools,
        "complete",
        lambda prompt, **kwargs: prompts.append(prompt)
        or ('[{"q":"Q?","options":["A","B","C","D"],"answer_index":0,"explain":"Evidence."}]'
            if kwargs["feature"] == "quiz"
            else '[{"front":"Concept?","back":"Evidence-based answer."}]'),
    )

    study_tools.make_quiz("topic")
    study_tools.make_flashcards("topic")

    for prompt in prompts:
        assert "EVIDENCE:" in prompt
        assert "Do not create cards about authors" in prompt or "Do not ask about authors" in prompt
        assert "Return fewer" in prompt