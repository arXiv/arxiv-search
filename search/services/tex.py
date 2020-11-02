"""Tools for dealing with tex from Elasticsearch in abstracts and titles."""

import re
from typing import List, Tuple, Union, Dict, Callable, Pattern, Any


class Math(str):
    """Marker class for tex strings."""

    def __math__(self):  # type: ignore
        """Similar to markupsafe."""
        return self


def isMath(checkme: Any) -> bool:
    """Checks if an object is Math."""
    if checkme is None:
        return False
    return hasattr(checkme, "__math__")


def position_f(delims: Dict[str, Tuple[str, Pattern]]) -> Callable[[str], List[Tuple[int, int]]]:
    """Return list of (start, end) of the locations of delimited txt."""

    # Build a Pattern for the combined start delimiters
    rstr = "|".join([f"({start})" for start, _ in delims.values()])
    starts = re.compile(rstr)

    def pos_func(txt: str) -> List[Tuple[int, int]]:
        record = []
        pos = 0
        start_match = starts.search(txt, pos)
        while start_match:
            start_pos1, start_pos2 = start_match.span()
            _, end_pat = delims[start_match.group(0)]
            end_match = end_pat.search(txt, start_pos2)
            if end_match:  # end found
                _, end_pos2 = end_match.span()
                record.append((start_pos1, end_pos2))
                pos = end_pos2
            else:  # end not found, just keep going
                pos = start_pos2

            start_match = starts.search(txt, pos)

        return record

    return pos_func


# These are the delimiters recoganized by MathJax
# represents start_regex_match: (start_regex_str, close_regex)
tex_delims = {
    "\\(": (r"\\\(", re.compile(r"\\\)")),
    "$$": (r"(?<!\\)\$\$", re.compile(r"\$\$")),
    "\\[": (r"\\\[", re.compile(r"\\]")),
    "$": (r"(?<!\\)\$", re.compile(r"\$(?!\$)")),
}

math_positions = position_f(tex_delims)
"""Gets list of positions of tex in a string"""


def split_for_maths(positions: List[Tuple[int, int]], txt: str) -> List[str]:
    """Splits the txt based on positions."""
    if not positions or not txt:
        return ['']

    pos = 0
    out = []
    for start, end in positions:
        if pos < start:
            out.append(txt[pos:start])
            out.append(Math(txt[start:end]))
            pos = end

    # add on anything left at the end
    out.append(txt[positions[-1][1]:])

    return out
