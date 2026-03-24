from __future__ import annotations

import requests
import os
import json
import time
import argparse


EXPECTED_MIN_POSTS = 50
EXPECTED_MIN_UNIQUE_USERS = 5
SAMPLE_SIZE = 3
API_URL = os.getenv("API_URL", "https://jsonplaceholder.typicode.com/posts")
DEFAULT_REPORT_FILENAME = "report.json"


def fetch_posts(api_url: str = API_URL) -> tuple[list[dict], float]:
    """Fetch posts from a public demo API and return posts plus response time."""
    try:
        start_time = time.perf_counter()
        response = requests.get(api_url, timeout=10)
        end_time = time.perf_counter()
        response_time = end_time - start_time
        response.raise_for_status()  # raises an error for 4xx/5xx
        data = response.json()

        if not isinstance(data, list):
            raise ValueError(f"Expected a list, got {type(data)}")

        return data, response_time

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out.")
        return [], 0.0
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        return [], 0.0
    except ValueError as e:
        print(f"ERROR: Bad data shape: {e}")
        return [], 0.0


def summarize_posts(posts: list[dict]) -> dict:
    """
    Return a summary dictionary for the posts data, including counts,
    user IDs, title analysis, and post IDs.
    """
    count = len(posts)

    user_ids = []
    post_ids = []
    long_title_count = 0
    qui_count = 0
    qui_titles = []
    all_titles = []

    for post in posts:
        # dict access + variables
        user_id = post.get("userId")
        post_id = post.get("id")
        title = post.get("title", "")

        if user_id is not None:
            user_ids.append(user_id)
        
        if post_id is not None:
            post_ids.append(post_id)

        if isinstance(title, str) and len(title) > 50:
            long_title_count += 1

        if isinstance(title, str) and "qui" in title.lower():
            qui_titles.append(title)
            qui_count += 1
        
        if isinstance(title, str):
            all_titles.append(title)

    unique_user_ids = sorted(set(user_ids))

    return {
        "count": count,
        "unique_user_ids": unique_user_ids,
        "titles_longer_than_50": long_title_count,
        "num_titles_with_qui": qui_count,
        "qui_titles": qui_titles,
        "all_titles": all_titles,
        "post_ids": post_ids,
    }


def validate_schema(posts: list[dict]) -> bool:
    for post in posts:
        if (
            not isinstance(post, dict)
            or "userId" not in post
            or "id" not in post
            or "title" not in post
        ):
            return False
    return True


def get_validation_results(summary: dict) -> list[dict]:
    results = []

    results.append({
        "name": "API returned a list",
        "passed": True,
    })

    results.append({
        "name": f"API returned >= {EXPECTED_MIN_POSTS} posts",
        "passed": summary["count"] >= EXPECTED_MIN_POSTS,
    })

    results.append({
        "name": f"API returned >= {EXPECTED_MIN_UNIQUE_USERS} unique users",
        "passed": len(summary["unique_user_ids"]) >= EXPECTED_MIN_UNIQUE_USERS,
    })

    empty_titles = [t for t in summary["all_titles"] if not t.strip()]

    results.append({
        "name": "No empty titles detected",
        "passed": len(empty_titles) == 0,
    })

    results.append({
        "name": "Found titles containing 'qui'",
        "passed": summary["num_titles_with_qui"] > 0,
    })

    results.append({
        "name": "Post IDs are unique",
        "passed": len(summary["post_ids"]) == len(set(summary["post_ids"])),
    })

    return results


def print_validation_results(results: list[dict]) -> None:
    print("\n=== VALIDATION RESULTS ===")
    
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}: {result['name']}")


    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed

    print("\n=== FINAL TEST SUMMARY ===")
    print(f"Total checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")


def save_report(
    results: list[dict], 
    summary: dict, 
    response_time: float,
    filename: str = DEFAULT_REPORT_FILENAME,
    api_url: str = API_URL,
) -> None:
    total = len(results)
    passed = sum(result["passed"] for result in results)
    failed = total - passed

    report_data = {
        "api_url": api_url,
        "response_time_seconds": round(response_time, 4), 
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "summary": {
            "count": summary["count"],
            "unique_user_ids": summary["unique_user_ids"],
            "titles_longer_than_50": summary["titles_longer_than_50"],
            "num_titles_with_qui": summary["num_titles_with_qui"],
            "total_titles": len(summary["all_titles"]),
        },
        "results": results,
    }

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report_data, file, indent=4)
    
    print(f"\nReport saved to {filename}")


def print_summary(summary: dict, sample_size: int) -> None:
    print("=== API Summary ===")
    print(f"Total posts: {summary['count']}")
    print(f"Unique user IDs: {summary['unique_user_ids']}")
    print(f"Titles > 50 chars: {summary['titles_longer_than_50']}")
    print(f"Total number of Titles: {len(summary['all_titles'])}")
    print("Titles (sample):")

    sample_titles = summary["all_titles"][:sample_size]
    for title in sample_titles:
        print(f"- {title}")

    remaining = len(summary["all_titles"]) - len(sample_titles)
    if remaining > 0:
        print(f"(and {remaining} more...)")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("sample size must be a positive integer")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the API smoke-check tool."""
    parser = argparse.ArgumentParser(
        description="Run API smoke checks against the configured posts endpoint."
    )

    parser.add_argument(
        "--sample",
        type=positive_int,
        default=SAMPLE_SIZE,
        help="Number of titles to print in the sample output.",
    )

    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT_FILENAME,
        help="Output JSON report filename (default: report.json).",
    )

    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    sample_size = args.sample
    report_filename = args.report

    print(f"Current api url: {API_URL}")

    posts, response_time = fetch_posts()

    if not posts:
        print("No posts returned. Exiting.")
        return

    print(f"Response time: {response_time:.4f} seconds")

    if not validate_schema(posts):
        print("Schema validation failed. Exiting.")
        return

    summary = summarize_posts(posts)

    print_summary(summary, sample_size)
    
    results = get_validation_results(summary)
    
    print_validation_results(results)

    save_report(results, summary, response_time, report_filename)

if __name__ == "__main__":
    main()