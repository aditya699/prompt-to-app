from __future__ import annotations

import pytest

from app.services.naming import project_name, slugify, with_suffix


@pytest.mark.parametrize(
    ("prompt", "name"),
    [
        ("Create a web app that will help me track my workout.", "Track My Workout"),
        (
            "Build an app to split trip expenses between friends",
            "Split Trip Expenses Between Friends",
        ),
        ("make a pomodoro timer", "Pomodoro Timer"),
        ("Create a web app that will help me track my workouts: log sets", "Track My Workouts"),
        ("Habit tracker with streaks", "Habit Tracker With Streaks"),
        ("Create a web app", "My App"),
        ("A khata book for a small shop", "Khata Book for a Small"),
    ],
)
def test_project_name(prompt: str, name: str) -> None:
    assert project_name(prompt) == name


def test_slug() -> None:
    assert slugify("Track My Workout!") == "track-my-workout"
    assert slugify("???") == "app"
    slug = with_suffix("todo")
    assert slug.startswith("todo-") and len(slug) == 9
