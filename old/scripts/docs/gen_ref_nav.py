"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()  # type: ignore

IGNORE = (
    ("_version",),
    # ('__init__',)
)

for path in Path("spotdl").glob("**/*.py"):
    module_path = path.relative_to("spotdl").with_suffix("")
    doc_path = path.relative_to("spotdl").with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    if module_path.parts in IGNORE:
        continue

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        if len(parts) != 1:
            parts = parts[:-1]

        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        if parts == ("__init__",):
            fd.write("::: spotdl")
            continue

        IDENT = "spotdl." + ".".join(parts)
        fd.write(f"::: {IDENT}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path)

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
