import pytest
from api_validator import summarize_posts, validate_schema, get_validation_results


@pytest.mark.parametrize(
    "posts, expected",
    [
        (
            [
                {"userId": 1, "id": 1, "title": "hello"},
                {"userId": 2, "id": 2, "title": "qui world"},
            ],
            True,
        ),
        (
            [
                {"userId": 1, "id": 1, "title": "hello"},
                {"userId": 2, "id": 2},
            ],
            False,
        ),
        (
            [],
            True,
        ),
    ], 
    ids = ["normal_posts","posts_with_missing_title","empty_posts"],
)

def test_validate_schema_accepts_mixed_inputs(posts, expected) -> None:
    assert validate_schema(posts) == expected

@pytest.mark.parametrize(
    "bad_input, expected_exception",
    [
        (None, TypeError),
        (123, TypeError),
    ],
    ids=["none_input", "int_input"],
)
def test_validate_schema_rejects_bad_inputs(bad_input, expected_exception) -> None:
    with pytest.raises(expected_exception):
        validate_schema(bad_input)

def test_validate_schema_returns_false_for_string_input() -> None:
    assert validate_schema("hello") is False

@pytest.mark.parametrize(
    "posts, expected",
    [
        (
            [
                {"userId": 1, "id": 1, "title": "hello"},
                {"userId": 2, "id": 2, "title": "qui world"},
            ],
            {
                "count": 2,
                "unique_user_ids": [1,2],
                "num_titles_with_qui": 1,
                "post_ids": [1,2],
            }
        ),
        (
            [],
            {
                "count": 0,
                "unique_user_ids": [],
                "num_titles_with_qui": 0,
                "post_ids": [],
            }
        ),
    ], ids = ["normal_posts", "empty_posts"],
)


def test_summarize_posts_returns_expected_summary(posts, expected) -> None:
    summary = summarize_posts(posts)

    assert summary["count"] == expected["count"]
    assert summary["unique_user_ids"] == expected["unique_user_ids"]
    assert summary["num_titles_with_qui"] == expected["num_titles_with_qui"]
    assert summary["post_ids"] == expected["post_ids"]

@pytest.mark.parametrize(
    "posts, check_type, expected",
    [
        (
            [
                {"userId": 1, "id": 1, "title": "one"},
                {"userId": 2, "id": 1, "title": "two"},
            ]
            ,"duplicate_ids",
            True,
        ),
        (
            [
                {"userId": 1, "id": 1, "title": "one"},
                {"userId": 2, "id": 2, "title": "two"},
            ]
            ,"duplicate_ids",
            False,
        ),
        (
            [
                {"userId": 1, "id": 1, "title": "Qui title"},
                {"userId": 1, "id": 2, "title": "QUI title"},
                {"userId": 2, "id": 3, "title": "qui title"},
                {"userId": 2, "id": 4, "title": "quiet room"},
                {"userId": 3, "id": 5, "title": "random"},
            ]
            ,"qui_count",
            4,
        ),
        (
            [
                {"userId": 1, "id": 1, "title": "short title"},
                {"userId": 1, "id": 2, "title": "a" * 50},
                {"userId": 2, "id": 3, "title": "b" * 51},
            ],"long_titles",
            1,
        ),
    ], ids=["duplicate_ids_detected", "no_duplicate_ids", "qui_case_insensitive", "num_long_titles"],
)

def test_summarize_posts_features(posts, check_type, expected) -> None:
    summary = summarize_posts(posts)

    if check_type == "duplicate_ids":
        duplicates_found = len(summary["post_ids"]) != len(set(summary["post_ids"]))
        assert duplicates_found == expected
    elif check_type == "qui_count":
        num_qui_titles = summary["num_titles_with_qui"]
        assert num_qui_titles == expected
    elif check_type == "long_titles":
        num_long_titles = summary["titles_longer_than_50"]
        assert num_long_titles == expected

@pytest.mark.parametrize(
    "bad_input, expected_exception",
    [
        (None, TypeError),
        ("not a list", AttributeError),
        (123, TypeError),
        ([1, 2, 3], AttributeError),
    ],
    ids=["none_input", "string_input", "int_input", "non_dict_items"],
)
def test_summarize_rejects_invalid_input_types(bad_input, expected_exception) -> None:
    with pytest.raises(expected_exception):
        summarize_posts(bad_input)


@pytest.mark.parametrize(
    "posts, expected",
    [
        (
            [{"userId": 1, "id": 1, "title": ""}],
            False,
        ),
        (
            [{"userId": 1, "id": 1, "title": "   "}],
            False,
        ),
        (
            [{"userId": 1, "id": 1, "title": "real title"}],
            True,
        ),
    ],
    ids=["empty_title", "whitespace_title", "normal_title"],
)

def test_get_validation_results_detects_empty_titles(posts, expected) -> None:
    
    summary = summarize_posts(posts)

    results = get_validation_results(summary)

    empty_titles_check = next((d for d in results if d["name"] == "No empty titles detected"), None)

    assert empty_titles_check is not None
    assert empty_titles_check["passed"] is expected