"""JSON serialisation rules for the API.

Two MySQL types do not survive `jsonify` unchanged, and both cause real
bugs in the browser:

  * DECIMAL arrives as Python `decimal.Decimal`. Flask serialises it as a
    **string**, so `mark_percent` reaches JavaScript as `"44.82"` rather
    than `44.82`. Chart.js silently plots nothing for string values, and
    `avg > 40` compares a string against a number - which in JavaScript
    is true for `"5"` and false for `"44.82"`, so the comparison is not
    merely wrong, it is wrong in a way that looks like it works.

  * DATE/DATETIME are serialised by Flask as RFC 822 ("Wed, 15 Jan 2025
    00:00:00 GMT"), which JavaScript's `new Date()` parses inconsistently
    across browsers. ISO 8601 is unambiguous.

Registering one provider on the app fixes both everywhere at once, rather
than every route remembering to convert its own numbers.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from flask.json.provider import DefaultJSONProvider


class ApiJSONProvider(DefaultJSONProvider):
    """Serialises database types the way a JSON client expects."""

    # Keys are emitted in the order the dict built them, rather than
    # alphabetically, so a response reads the way the code wrote it.
    sort_keys = False

    @staticmethod
    def default(obj):
        if isinstance(obj, Decimal):
            # Percentages and marks do not need decimal precision, and a
            # float is what every consumer of this API actually wants.
            return float(obj)

        if isinstance(obj, datetime):
            # The driver hands back *naive* datetimes. The connection
            # pins its session to UTC (see db.py), so a naive value from
            # the database is UTC - it just is not labelled as such.
            #
            # Sending it unlabelled is a real bug, not a cosmetic one:
            # `new Date("2026-08-04T17:55:58")` in JavaScript interprets a
            # timezone-less string as *local* time, so a login that
            # happened seconds ago rendered as "5h ago" for a viewer in
            # IST. Stamping the offset lets the browser convert properly.
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=UTC)
            return obj.isoformat()

        if isinstance(obj, (date, time)):
            # A plain date has no time zone to speak of - an assessment
            # dated the 3rd is the 3rd everywhere.
            return obj.isoformat()

        if isinstance(obj, timedelta):
            return obj.total_seconds()

        if isinstance(obj, (bytes, bytearray)):
            return obj.decode("utf-8", errors="replace")

        if isinstance(obj, set):
            return sorted(obj)

        return DefaultJSONProvider.default(obj)
