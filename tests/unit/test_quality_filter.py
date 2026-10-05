from learning_assistant.retrieval_services.quality_filter import is_front_matter


def test_filters_dedication_heading():
    assert is_front_matter({"heading": "Dedication", "content": "For my family."})


def test_filters_front_matter_from_first_content_line():
    assert is_front_matter(
        {"heading": None, "content": "Acknowledgements\nThanks to everyone."}
    )


def test_keeps_subject_matter_passages():
    assert not is_front_matter(
        {"heading": "Chapter 2", "content": "A neural network learns patterns."}
    )