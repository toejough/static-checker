# coding: utf-8


"""Source Control."""


# [ Imports ]
# [ -Python ]
import asyncio
import concurrent.futures
import select
import sys
import termios
from pathlib import Path
from typing import Sequence
# [ -Project ]
from ..interactors.runner import run


# [ Helpers ]
async def _get_status() -> Sequence[str]:
    """Get repo status."""
    return (await run('git', ['status', '--porcelain'])).output.splitlines()


async def _add_missing_paths(paths: Sequence[Path], status_lines: Sequence[str]) -> None:
    """Add any missing paths to the repo."""
    if not status_lines:
        return
    new_file_lines = [l for l in status_lines if l.startswith('??')]
    new_path_strings = [v for l in new_file_lines for k, v in [l.split()]]
    for path in paths:
        path_string = str(path)
        if path_string in new_path_strings or (
            any(nps.endswith('/') and path_string.startswith(nps) for nps in new_path_strings)
        ):
            await run('git', ['add', path_string])


async def async_input(prompt: str) -> str:
    """Async input prompt."""
    readable = []  # type: List[int]
    print(prompt, end='')
    sys.stdout.flush()
    while not readable:
        readable, writeable, executable = select.select([sys.stdin], [], [], 0)
        try:
            await asyncio.sleep(0.1)
        except concurrent.futures.CancelledError:
            print("input cancelled...")
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
            raise
    return sys.stdin.readline().rstrip()


# [ API ]
async def commit(paths: Sequence[Path]) -> bool:
    """Commit the current repo."""
    status_lines = await _get_status()
    await _add_missing_paths(paths, status_lines)
    status_lines = await _get_status()
    modified_file_lines = [l for l in status_lines if not l.startswith('??')]
    if not modified_file_lines:
        print("No actual changes made - nothing to commit.")
        return True
    print((await run('git', ['diff', '--color'])).output)
    try:
        print("Files are still being watched, and further changes will cancel this dialog")
        print("  and re-run the checks, but you may commit the above changes now by")
        print("  entering a commit message.")
        print()
        message = await async_input('> ')
    except concurrent.futures.CancelledError:
        raise
    return (await run('git', ['commit', '-am', message])).success