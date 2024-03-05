import arrow
from invenio_records.dumpers.search import SearchDumperExt


class IndexedAtDumperExt(SearchDumperExt):
    """Dumper for the indexed_at field."""

    def __init__(self, key="indexed_at"):
        """Initialize the dumper."""
        self.key = key

    def dump(self, record, data):
        """Dump relations."""
        data[self.key] = arrow.utcnow().isoformat()

    def load(self, data, record_cls):
        """Load (remove) indexed data."""
        data.pop(self.key, None)


class RemoveSchemaDumperExt(SearchDumperExt):
    """Dumper for the indexed_at field."""

    def __init__(self, key="$schema"):
        """Initialize the dumper."""
        self.key = key

    def dump(self, record, data):
        """Remove $schema."""
        data.pop(self.key, None)

    def load(self, data, record_cls):
        """Add back to data."""
        data["$schema"] = record_cls.schema
