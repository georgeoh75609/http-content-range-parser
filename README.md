# http-content-range-parser

Parse HTTP `Content-Range` header values into `start`, `end`, and `total` fields. Handles the satisfied form (`bytes 0-1023/2048`), the satisfied-but-unknown-total form (`bytes 0-1023/*`), and the unsatisfied form (`bytes */2048`).

## Usage

```python
from http_content_range_parser import ContentRange, ContentRangeParseError

cr = ContentRange.parse("bytes 0-1023/2048")
assert cr.start == 0
assert cr.end == 1023
assert cr.total == 2048

unknown = ContentRange.parse("bytes 0-1023/*")
assert unknown.total is None

unsatisfied = ContentRange.parse("bytes */2048")
assert unsatisfied.start is None
assert unsatisfied.end is None
assert unsatisfied.total == 2048

try:
    ContentRange.parse("bytes 5-2/10")
except ContentRangeParseError:
    pass
```

The parser returns a frozen dataclass with four fields: `unit` (always `"bytes"` here), `start`, `end`, and `total`. Any field not present in the header is `None`. `ContentRangeParseError` subclasses `ValueError`, so existing `except ValueError` handlers keep working.

## Why this exists

Servers emit three grammatically distinct shapes of `Content-Range`, and callers usually want one uniform record. A single regex tends to either accept nonsense like `bytes 5-2/10` (end before start) or reject the unsatisfied form `bytes */total`, which is the whole point of the 416 response. This library parses each form by structure rather than by pattern, and rejects the impossible combinations explicitly.

The deliberate trade-off: only the `bytes` unit is supported. RFC 9110's grammar is unit-agnostic, but no other unit is in registered use, and accepting `items 0-1/10` would return a record whose semantics nobody can act on. Refusing it is safer than pretending.

## Awkward edge

`bytes */*` is rejected. The unsatisfied-range form exists specifically to tell the client the real total size after a 416, so a server sending `*/*` is not conformant and the parser refuses to guess.
