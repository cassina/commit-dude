import textwrap

from commit_dude.core.config import COMMIT_LINE_LENGTH
from commit_dude.core.utils import wrap_commit_message


def test_wrap_commit_message_wraps_breaking_change_footer():
    message = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports

        - rename commit_dude/core/agents.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(message, max_len=COMMIT_LINE_LENGTH)
    lines = wrapped.splitlines()

    assert any(line.startswith("BREAKING CHANGE:") for line in lines)
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)


def test_wrap_commit_message_wraps_multiple_breaking_change_footers():
    message = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports

        - rename commit_dude/core/agents.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(message, max_len=COMMIT_LINE_LENGTH)
    lines = wrapped.splitlines()

    breaking_change_lines = [line for line in lines if line.startswith("BREAKING CHANGE:")]

    assert len(breaking_change_lines) == 2
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)


def test_wrap_commit_message_wraps_main_example_without_exceeding_limit():
    main_example = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py

        - rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(main_example, max_len=COMMIT_LINE_LENGTH)

    lines = wrapped.splitlines()

    assert lines.count("") == 2
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)


def test_wrap_commit_message_wraps_main_example_bullet_continuations_with_indent():
    main_example = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py

        - rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(main_example, max_len=COMMIT_LINE_LENGTH)
    bullet_lines = [line for line in wrapped.splitlines() if line.startswith("- ")]

    assert len(bullet_lines) == 4
    assert all(line.startswith("  ") for line in wrapped.splitlines() if line.startswith("  "))
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in wrapped.splitlines() if line)


def test_wrap_commit_message_wraps_main_example_breaking_change_alignment():
    main_example = textwrap.dedent(
        """
        refactor(core)!: reorganize modules and update imports rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py

        - rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py rename commit_dude/core/agents.py -> commit_dude/core/agents.py
        - move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py move commit_dude/utils.py -> commit_dude/core/utils.py
        - update imports in cli, service, middleware, and tests
        - add empty commit_dude/shared package

        BREAKING CHANGE: update external imports: commit_dude.core.factory -> commit_dude.core.agents; commit_dude.utils -> commit_dude.core.utils
        """
    ).strip()

    wrapped = wrap_commit_message(main_example, max_len=COMMIT_LINE_LENGTH)
    lines = wrapped.splitlines()

    breaking_change_line_index = next(
        index for index, line in enumerate(lines) if line.startswith("BREAKING CHANGE:")
    )
    following_lines = lines[breaking_change_line_index + 1 :]

    assert lines[breaking_change_line_index].startswith("BREAKING CHANGE:")
    assert all(not line.startswith(" ") for line in following_lines if line)
    assert all(len(line) <= COMMIT_LINE_LENGTH for line in lines if line)
