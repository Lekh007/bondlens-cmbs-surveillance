import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

from vichara_portfolio.bondlens.adapters.filing_store import FilingDocument
from vichara_portfolio.bondlens.domain import (
    Deal,
    ParsedAssetData,
    SecFiling,
    SubmissionsResult,
)
from vichara_portfolio.bondlens.service import BondLensService
from vichara_portfolio.shared.provenance import SourceRef
from vichara_portfolio.shared.storage import StoredDocument


def _filing(accession: str, *, filing_date: date = date(2026, 7, 30)) -> SecFiling:
    return SecFiling(
        cik="0002110410",
        accession_number=accession,
        form_type="ABS-EE",
        filing_date=filing_date,
        report_date=filing_date,
        primary_document=f"bmk_absee_{accession}.htm",
    )


def _source(label: str) -> SourceRef:
    return SourceRef(
        source_name="sec_edgar",
        source_url=f"https://www.sec.gov/x/{label}",
        retrieved_at=datetime(2026, 8, 28, 12, 0, tzinfo=UTC),
    )


class FakeSecEdgar:
    def __init__(
        self,
        filings: tuple[SecFiling, ...],
        *,
        entity_name: str = "Benchmark 2026-B42 Mortgage Trust",
    ) -> None:
        self._filings = filings
        self._entity_name = entity_name

    def list_filings(self, cik, *, forms=None):
        return SubmissionsResult(
            entity_name=self._entity_name, filings=self._filings, source=_source("submissions")
        )


@dataclass
class FakeFilingStore:
    documents_by_accession: dict[str, tuple[FilingDocument, ...]] = field(default_factory=dict)
    fail_on_list: set[str] = field(default_factory=set)
    xml_bytes: bytes = (
        b"<assetData xmlns='http://www.sec.gov/edgar/document/absee/cmbs/assetdata'/>"
    )

    def list_documents(self, *, cik, accession):
        if accession in self.fail_on_list:
            raise ConnectionError(f"simulated network failure for {accession}")
        documents = self.documents_by_accession.get(accession, ())
        return documents, _source(f"list-{accession}")

    def download(self, document, *, accession, allowed_content_types):
        # StoredDocument.path must be a real, readable file - the service
        # calls stored.path.read_bytes() on it, same as the real FilingStore.
        tmp_dir = Path(tempfile.mkdtemp(prefix="bondlens-fake-filing-store-"))
        path = tmp_dir / document.filename
        path.write_bytes(self.xml_bytes)
        stored = StoredDocument(
            source="sec", checksum="fake", path=path, size=len(self.xml_bytes), already_cached=False
        )
        return stored, _source(f"download-{accession}")


@dataclass
class FakeRepository:
    deals: list[Deal] = field(default_factory=list)
    filings: list[SecFiling] = field(default_factory=list)
    source_documents: list[SourceRef] = field(default_factory=list)
    saved: list[tuple[str, ParsedAssetData]] = field(default_factory=list)

    def upsert_deal(self, deal: Deal) -> None:
        self.deals.append(deal)

    def upsert_filing(self, filing: SecFiling) -> None:
        self.filings.append(filing)

    def upsert_source_document(self, source: SourceRef) -> int:
        self.source_documents.append(source)
        return len(self.source_documents)

    def save_parsed_asset_data(self, *, accession_number, parsed, source_document_id):
        self.saved.append((accession_number, parsed))
        return len(parsed.loans), sum(len(loan.properties) for loan in parsed.loans)

    @contextmanager
    def savepoint(self):
        yield


def _fake_parse(xml_bytes: bytes, source: SourceRef) -> ParsedAssetData:
    return ParsedAssetData(loans=(), issues=())


def _service(
    sec: FakeSecEdgar, filing_store: FakeFilingStore, repo: FakeRepository
) -> BondLensService:
    return BondLensService(sec, filing_store, repo, parse=_fake_parse)


def test_ingest_deal_upserts_the_deal_once() -> None:
    sec = FakeSecEdgar((_filing("acc-1"),))
    filing_store = FakeFilingStore(
        documents_by_accession={
            "acc-1": (FilingDocument("EX-102", "exh_102.xml", "https://www.sec.gov/x"),)
        }
    )
    repo = FakeRepository()

    _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert len(repo.deals) == 1
    assert repo.deals[0].cik == "0002110410"
    assert repo.deals[0].name == "Benchmark 2026-B42 Mortgage Trust"


def test_ingest_deal_with_no_filings_is_a_no_op_success() -> None:
    sec = FakeSecEdgar(())
    filing_store = FakeFilingStore()
    repo = FakeRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.total_filings == 0
    assert summary.created_count == 0
    assert summary.failed_count == 0


def test_filing_with_no_ex102_exhibit_is_skipped_not_failed() -> None:
    sec = FakeSecEdgar((_filing("acc-no-exhibit"),))
    filing_store = FakeFilingStore(
        documents_by_accession={
            "acc-no-exhibit": (FilingDocument("ABS-EE", "cover.htm", "https://x"),)
        }
    )
    repo = FakeRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.skipped_count == 1
    assert summary.created_count == 0
    assert summary.failed_count == 0
    assert summary.outcomes[0].status == "skipped"
    assert summary.outcomes[0].reason is not None


def test_filing_that_raises_during_list_is_failed_not_a_crash() -> None:
    sec = FakeSecEdgar((_filing("acc-broken"),))
    filing_store = FakeFilingStore(fail_on_list={"acc-broken"})
    repo = FakeRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.failed_count == 1
    assert summary.outcomes[0].status == "failed"
    assert "simulated network failure" in (summary.outcomes[0].reason or "")


def test_one_failure_does_not_stop_ingestion_of_the_rest() -> None:
    sec = FakeSecEdgar((_filing("acc-broken"), _filing("acc-ok")))
    filing_store = FakeFilingStore(
        fail_on_list={"acc-broken"},
        documents_by_accession={"acc-ok": (FilingDocument("EX-102", "exh_102.xml", "https://x"),)},
    )
    repo = FakeRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.total_filings == 2
    assert summary.failed_count == 1
    assert summary.created_count == 1


@dataclass
class PoisonableRepository:
    """Simulates a shared DB session/transaction: once a write raises, the
    session is 'poisoned' and every subsequent write also raises - unless
    something rolls it back to a savepoint first, the way a real Postgres
    session requires. Regression test for a real bug (2026-08-28): without
    _ingest_one_filing wrapping its writes in repository.savepoint(), one
    bad filing poisoned every filing after it in the same ingest_deal run."""

    fail_for_accession: str | None = None
    saved: list[str] = field(default_factory=list)
    _poisoned: bool = False

    def upsert_deal(self, deal: Deal) -> None:
        pass

    def upsert_filing(self, filing: SecFiling) -> None:
        pass

    def upsert_source_document(self, source: SourceRef) -> int:
        return 1

    def save_parsed_asset_data(self, *, accession_number, parsed, source_document_id):
        if self._poisoned:
            raise RuntimeError("session is poisoned - needs a rollback before further writes")
        if accession_number == self.fail_for_accession:
            self._poisoned = True
            raise ValueError(f"simulated DB failure for {accession_number}")
        self.saved.append(accession_number)
        return len(parsed.loans), 0

    @contextmanager
    def savepoint(self):
        try:
            yield
        except Exception:
            self._poisoned = False  # a real ROLLBACK TO SAVEPOINT clears this
            raise


def test_one_filings_db_failure_does_not_poison_the_rest_of_the_ingest() -> None:
    sec = FakeSecEdgar((_filing("acc-good-1"), _filing("acc-bad"), _filing("acc-good-2")))
    filing_store = FakeFilingStore(
        documents_by_accession={
            accession: (FilingDocument("EX-102", "exh_102.xml", "https://x"),)
            for accession in ("acc-good-1", "acc-bad", "acc-good-2")
        }
    )
    repo = PoisonableRepository(fail_for_accession="acc-bad")

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.created_count == 2
    assert summary.failed_count == 1
    assert repo.saved == ["acc-good-1", "acc-good-2"]


def test_successful_ingest_persists_source_document_and_asset_data() -> None:
    sec = FakeSecEdgar((_filing("acc-1"),))
    filing_store = FakeFilingStore(
        documents_by_accession={"acc-1": (FilingDocument("EX-102", "exh_102.xml", "https://x"),)}
    )
    repo = FakeRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.created_count == 1
    assert len(repo.source_documents) == 1
    assert len(repo.saved) == 1
    assert repo.saved[0][0] == "acc-1"
    assert len(repo.filings) == 1
    assert repo.filings[0].accession_number == "acc-1"


@dataclass
class FkEnforcingRepository:
    """Simulates the real Postgres FK: cmbs_reporting_periods.accession_number
    references cmbs_filings.accession_number, so save_parsed_asset_data must
    fail unless upsert_filing already wrote that accession. Regression test
    for a real bug (2026-08-28, live SEC/Postgres run): _ingest_one_filing
    never called repository.upsert_filing, so every filing failed with
    psycopg.errors.ForeignKeyViolation on cmbs_reporting_periods - invisible
    to the plain FakeRepository above because it has no FK to enforce."""

    known_accessions: set[str] = field(default_factory=set)
    saved: list[str] = field(default_factory=list)

    def upsert_deal(self, deal: Deal) -> None:
        pass

    def upsert_filing(self, filing) -> None:
        self.known_accessions.add(filing.accession_number)

    def upsert_source_document(self, source: SourceRef) -> int:
        return 1

    def save_parsed_asset_data(self, *, accession_number, parsed, source_document_id):
        if accession_number not in self.known_accessions:
            raise RuntimeError(
                f"ForeignKeyViolation: {accession_number} not present in cmbs_filings"
            )
        self.saved.append(accession_number)
        return len(parsed.loans), 0

    @contextmanager
    def savepoint(self):
        yield


def test_ingest_deal_upserts_the_filing_before_saving_its_asset_data() -> None:
    sec = FakeSecEdgar((_filing("acc-1"),))
    filing_store = FakeFilingStore(
        documents_by_accession={"acc-1": (FilingDocument("EX-102", "exh_102.xml", "https://x"),)}
    )
    repo = FkEnforcingRepository()

    summary = _service(sec, filing_store, repo).ingest_deal("0002110410")

    assert summary.created_count == 1
    assert summary.failed_count == 0
    assert repo.saved == ["acc-1"]


def test_ingestion_is_idempotent_at_the_service_level_two_runs_same_counts() -> None:
    """The service calls upsert_* methods every time - true idempotency (no
    duplicate rows) is the repository's contract, verified against real
    Postgres in Task 9. Here we verify the service issues the same calls on
    a re-run rather than accumulating extra state of its own."""
    sec = FakeSecEdgar((_filing("acc-1"),))
    filing_store = FakeFilingStore(
        documents_by_accession={"acc-1": (FilingDocument("EX-102", "exh_102.xml", "https://x"),)}
    )
    repo = FakeRepository()
    service = _service(sec, filing_store, repo)

    first = service.ingest_deal("0002110410")
    second = service.ingest_deal("0002110410")

    assert first.created_count == second.created_count == 1
