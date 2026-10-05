import re

_FRONT_MATTER = re.compile(
    r"^(?:dedicat(?:ion|ed|es|ing)|acknowledg(?:e)?ments?|foreword|preface|"
    r"table\s+of\s+contents|contents|about\s+the\s+author|copyright)\b",
    re.IGNORECASE,
)


def is_front_matter(document: dict) -> bool:
    heading = str(document.get("heading") or "").strip()
    content = str(document.get("content") or "")
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    return bool(_FRONT_MATTER.match(heading) or _FRONT_MATTER.match(first_line))