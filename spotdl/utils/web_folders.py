"""Confined destinations for web downloads."""

from pathlib import Path


def music_root(output: str) -> Path:
    """Return the directory before the first filename template component."""
    path = Path(output).expanduser()
    parts = []
    for part in path.parts:
        if "{" in part:
            break
        parts.append(part)
    if len(parts) == len(path.parts):
        return path.parent.resolve()
    return Path(*parts).resolve() if parts else Path.cwd().resolve()


def folder_destination(output: str, name: str, create: bool = False) -> str:
    """Select an existing child directory, optionally creating it."""
    if not name:
        return output
    if (
        name in (".", "..")
        or any(c in name for c in '/\\{}<>:"|?*')
        or any(ord(c) < 32 for c in name)
        or name.endswith((" ", "."))
        or name.split(".")[0].upper()
        in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)],
        }
    ):
        raise ValueError("Choose a single valid folder name.")
    root = music_root(output)
    target = root / name
    if target.is_symlink() or target.resolve().parent != root:
        raise ValueError("The folder must remain inside the music directory.")
    if create:
        target.mkdir(exist_ok=True)
    if not target.is_dir():
        raise ValueError("The selected folder does not exist.")
    return str(target / "{artists} - {title}.{output-ext}")


def music_folders(output: str) -> list[str]:
    """List direct child directories without following symbolic links."""
    root = music_root(output)
    if not root.is_dir():
        return []
    return sorted(
        (
            item.name
            for item in root.iterdir()
            if item.is_dir() and not item.is_symlink()
        ),
        key=str.casefold,
    )
