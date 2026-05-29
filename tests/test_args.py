"""The small getopt-ish argument splitter."""

from __future__ import annotations

from cascade.shell.commands._args import parse_args


def test_positionals_only():
    flags, values, positionals = parse_args(["a", "b"])
    assert flags == set()
    assert values == {}
    assert positionals == ["a", "b"]


def test_combined_short_flags():
    flags, _, positionals = parse_args(["-la", "/x"])
    assert flags == {"l", "a"}
    assert positionals == ["/x"]


def test_valued_short_flag_separate():
    _, values, positionals = parse_args(["-n", "5", "f"], valued=("n",))
    assert values == {"n": "5"}
    assert positionals == ["f"]


def test_valued_short_flag_attached():
    _, values, _ = parse_args(["-n5"], valued=("n",))
    assert values == {"n": "5"}


def test_long_flag_and_valued():
    flags, values, _ = parse_args(["--follow", "--name", "x"], valued=("name",))
    assert "follow" in flags
    assert values == {"name": "x"}


def test_double_dash_terminates_options():
    flags, _, positionals = parse_args(["--", "-notaflag"])
    assert flags == set()
    assert positionals == ["-notaflag"]


def test_negative_number_is_positional():
    _, _, positionals = parse_args(["-5"])
    assert positionals == ["-5"]
