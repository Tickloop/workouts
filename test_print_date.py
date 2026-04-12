import subprocess
import sys
from datetime import date
from io import StringIO
from unittest import mock

import pytest

from print_date import get_today, main


def test_get_today_returns_date():
    result = get_today()
    assert isinstance(result, date)


def test_get_today_matches_todays_date():
    result = get_today()
    assert result == date.today()


def test_main_prints_todays_date(capsys):
    main()
    captured = capsys.readouterr()
    assert captured.out.strip() == str(date.today())


def test_main_output_is_valid_iso_date(capsys):
    main()
    captured = capsys.readouterr()
    output = captured.out.strip()
    parsed = date.fromisoformat(output)
    assert isinstance(parsed, date)


def test_main_with_mocked_date(capsys):
    fixed_date = date(2026, 1, 15)
    with mock.patch("print_date.date") as mock_date:
        mock_date.today.return_value = fixed_date
        main()
    captured = capsys.readouterr()
    assert captured.out.strip() == "2026-01-15"


def test_script_runs_as_main():
    result = subprocess.run(
        [sys.executable, "print_date.py"],
        capture_output=True,
        text=True,
        cwd="/workspace",
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(date.today())
