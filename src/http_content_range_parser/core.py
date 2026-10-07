"""Parse RFC 9110 Content-Range header values.

The header grammar is one of

    bytes 0-1023/2048      a satisfied byte range over a known total
    bytes 0-1023/*         a satisfied byte range, total unknown
    bytes */2048           an unsatisfied range; the client asked past EOF

This module turns those three forms into a small, immutable record whose
fields are either ints or ``None``.  ``None`` means "not present in the
header"; the caller decides whether that is acceptable.

Why a dedicated parser instead of a regex
-----------------------------------------
The three forms look similar but are semantically different, and naive
regexes frequently accept malformed values such as ``bytes 5-3/10`` where
end < start, or ``bytes */*`` which is never valid under RFC 9110.
Hand-written structural parsing lets us reject those precisely, rather
than silently returning something that looks usable.
"""

from __future__ import annotations

from dataclasses import dataclass


class ContentRangeParseError(ValueError):
    """Raised when a Content-Range header cannot be parsed.

    Subclasses ValueError so callers that already catch ValueError for
    header validation keep working without importing this class.
    """


@dataclass(frozen=True)
class ContentRange:
    """A parsed Content-Range header.

    Attributes:
        unit: The range unit as it appeared in the header, lower-cased
            and stripped of surrounding whitespace.  RFC 9110 only
            defines ``bytes``; other units are syntactically valid so
            they are preserved here rather than being rejected.
        start: Inclusive start byte offset.  ``None`` when the header is
            an unsatisfied-range form (``bytes */total``).
        end: Inclusive end byte offset.  ``None`` when the header is an
            unsatisfied-range form.
        total: The complete representation size, or ``None`` when the
            total is unknown (``*/``).  Always present for unsatisfied
            ranges, because RFC 9110 requires the server to report the
            current total there.

    The fields are deliberately plain ints/None rather than a custom
    sentinel type: the header grammar has no concept of "zero means
    absent", and None is the conventional Python way to say "not
    supplied".  Callers that need to distinguish ``0`` from "unknown"
    can do so with ``is None``.
    """

    unit: str
    start: int | None
    end: int | None
    total: int | None

    @classmethod
    def parse(cls, header: str) -> "ContentRange":
        """Parse a Content-Range header value.

        Raises:
            ContentRangeParseError: if the value is empty, malformed,
                carries a non-byte unit (we only know how to interpret
                ``bytes``), or describes an impossible range such as
                ``bytes 5-2/10``.
        """
        if not isinstance(header, str):
            raise ContentRangeParseError(
                "Content-Range header must be a string"
            )

        text = header.strip()
        if not text:
            raise ContentRangeParseError("Content-Range header is empty")

        # Split exactly once on the first SP.  RFC 9110 allows a single
        # space between the unit and the range; anything looser here would
        # accept headers servers never send and normalise away real
        # formatting bugs.
        parts = text.split(" ", 1)
        if len(parts) != 2:
            raise ContentRangeParseError(
                f"Content-Range must contain a space separating unit and range: {header!r}"
            )
        unit, range_part = parts

        unit = unit.lower()
        if unit != "bytes":
            # The grammar is unit-agnostic but the only registered unit is
            # "bytes".  Accepting "items 0-1/10" would silently return a
            # record whose semantics nobody can interpret, so we refuse.
            raise ContentRangeParseError(
                f"unsupported Content-Range unit {unit!r}; only 'bytes' is supported"
            )

        if "/" not in range_part:
            raise ContentRangeParseError(
                f"Content-Range missing '/' separator: {range_part!r}"
            )
        range_spec, total_spec = range_part.split("/", 1)

        if range_spec.startswith("*"):
            # Unsatisfied-range form: bytes */total
            if range_spec != "*":
                raise ContentRangeParseError(
                    f"invalid unsatisfied-range specifier {range_spec!r}; expected '*'"
                )
            if total_spec == "*":
                # RFC 9110 forbids bytes */*: the whole point of the
                # unsatisfied form is to tell the client the real total.
                raise ContentRangeParseError(
                    "unsatisfied Content-Range must report a concrete total, got '*'"
                )
            total = _parse_non_negative_int(total_spec)
            return cls(unit=unit, start=None, end=None, total=total)

        # Satisfied-range form: bytes start-end/total
        if "-" not in range_spec:
            raise ContentRangeParseError(
                f"byte range missing '-' separator: {range_spec!r}"
            )
        start_spec, end_spec = range_spec.split("-", 1)
        start = _parse_non_negative_int(start_spec)
        end = _parse_non_negative_int(end_spec)
        if end < start:
            raise ContentRangeParseError(
                f"Content-Range end ({end}) is less than start ({start})"
            )

        if total_spec == "*":
            total = None
        else:
            total = _parse_non_negative_int(total_spec)

        return cls(unit=unit, start=start, end=end, total=total)


_SENTINEL = object()


def _parse_non_negative_int(text: str) -> int:
    """Parse a decimal non-negative integer with no leading zeros allowed.

    We forbid leading zeros (``007``) so that we do not silently accept
    values a stricter caller might later format differently, and we do
    not call int() and then re-stringify to compare, because that would
    treat ``+5`` as valid — the Content-Range grammar does not.
    """
    if not text:
        raise ContentRangeParseError("expected an integer, got empty string")
    if text == "0":
        return 0
    if not text.isdigit() or text[0] == "0":
        raise ContentRangeParseError(f"invalid non-negative integer {text!r}")
    return int(text)
