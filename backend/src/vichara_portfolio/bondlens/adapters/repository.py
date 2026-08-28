"""SQLAlchemy models and repository for normalized CMBS data.

Idempotency contract: re-running the same ingest against the same source
data must not change row counts. cmbs_deals/cmbs_filings/
cmbs_reporting_periods/cmbs_assets/cmbs_property_snapshots use Postgres
`INSERT ... ON CONFLICT DO UPDATE` keyed on their natural business key
(cik; accession_number; accession_number; (accession_number,
asset_number); (asset_id, property_index)) - never an autoincrement id,
which would happily duplicate. source_documents dedupes by checksum via
a plain select-then-insert, since not every SourceRef has a checksum
(the submissions JSON endpoint isn't a fixed downloaded artifact).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, insert
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from vichara_portfolio.bondlens.domain import Deal, Loan, ParsedAssetData, SecFiling
from vichara_portfolio.shared.db import Base
from vichara_portfolio.shared.provenance import SourceRef


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


class SourceDocumentRow(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String, nullable=True)
    field_path: Mapped[str | None] = mapped_column(String, nullable=True)


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_cik: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class DealRow(Base):
    __tablename__ = "cmbs_deals"

    cik: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class FilingRow(Base):
    __tablename__ = "cmbs_filings"

    accession_number: Mapped[str] = mapped_column(String, primary_key=True)
    cik: Mapped[str] = mapped_column(String, ForeignKey("cmbs_deals.cik"), nullable=False)
    form_type: Mapped[str] = mapped_column(String, nullable=False)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    primary_document: Mapped[str] = mapped_column(String, nullable=False)


class ReportingPeriodRow(Base):
    __tablename__ = "cmbs_reporting_periods"
    __table_args__ = (UniqueConstraint("accession_number", name="uq_reporting_period_accession"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_number: Mapped[str] = mapped_column(
        String, ForeignKey("cmbs_filings.accession_number"), nullable=False
    )
    beginning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ending_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class AssetRow(Base):
    __tablename__ = "cmbs_assets"
    __table_args__ = (
        UniqueConstraint("accession_number", "asset_number", name="uq_asset_accession_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_number: Mapped[str] = mapped_column(
        String, ForeignKey("cmbs_filings.accession_number"), nullable=False
    )
    asset_number: Mapped[str] = mapped_column(String, nullable=False)
    group_id: Mapped[str | None] = mapped_column(String, nullable=True)
    originator_name: Mapped[str | None] = mapped_column(String, nullable=True)
    origination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_loan_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    original_interest_rate_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric, nullable=True
    )
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_through_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    scheduled_principal_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    scheduled_interest_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    actual_balance_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    scheduled_balance_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    payment_status_code: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_document_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("source_documents.id"), nullable=True
    )

    properties: Mapped[list[PropertySnapshotRow]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class PropertySnapshotRow(Base):
    __tablename__ = "cmbs_property_snapshots"
    __table_args__ = (
        UniqueConstraint("asset_id", "property_index", name="uq_property_asset_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("cmbs_assets.id"), nullable=False)
    property_index: Mapped[int] = mapped_column(Integer, nullable=False)
    property_name: Mapped[str] = mapped_column(String, nullable=False)
    property_address: Mapped[str | None] = mapped_column(String, nullable=True)
    property_city: Mapped[str | None] = mapped_column(String, nullable=True)
    property_state: Mapped[str | None] = mapped_column(String, nullable=True)
    property_zip: Mapped[str | None] = mapped_column(String, nullable=True)
    property_county: Mapped[str | None] = mapped_column(String, nullable=True)
    property_type_code: Mapped[str | None] = mapped_column(String, nullable=True)
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_rentable_square_feet: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    at_securitization: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    most_recent: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    raw_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    asset: Mapped[AssetRow] = relationship(back_populates="properties")


class DataQualityIssueRow(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accession_number: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_number: Mapped[str | None] = mapped_column(String, nullable=True)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    raw_value: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


class BondLensRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @contextmanager
    def savepoint(self) -> Iterator[None]:
        with self._session.begin_nested():
            yield

    def upsert_source_document(self, source: SourceRef) -> int:
        if source.checksum is not None:
            existing = self._session.execute(
                select(SourceDocumentRow.id).where(SourceDocumentRow.checksum == source.checksum)
            ).scalar_one_or_none()
            if existing is not None:
                return existing

        row = SourceDocumentRow(
            source_name=source.source_name,
            source_url=source.source_url,
            checksum=source.checksum,
            retrieved_at=source.retrieved_at,
            record_id=source.record_id,
            field_path=source.field_path,
        )
        self._session.add(row)
        self._session.flush()
        return row.id

    def upsert_deal(self, deal: Deal) -> None:
        stmt = insert(DealRow).values(cik=deal.cik, name=deal.name)
        stmt = stmt.on_conflict_do_update(index_elements=["cik"], set_={"name": stmt.excluded.name})
        self._session.execute(stmt)

    def upsert_filing(self, filing: SecFiling) -> None:
        stmt = insert(FilingRow).values(
            accession_number=filing.accession_number,
            cik=filing.cik,
            form_type=filing.form_type,
            filing_date=filing.filing_date,
            report_date=filing.report_date,
            primary_document=filing.primary_document,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["accession_number"],
            set_={
                "form_type": stmt.excluded.form_type,
                "filing_date": stmt.excluded.filing_date,
                "report_date": stmt.excluded.report_date,
                "primary_document": stmt.excluded.primary_document,
            },
        )
        self._session.execute(stmt)

    def save_parsed_asset_data(
        self, *, accession_number: str, parsed: ParsedAssetData, source_document_id: int | None
    ) -> tuple[int, int]:
        """Upserts every loan and its properties for one filing. Returns
        (loans_written, properties_written)."""
        if parsed.loans:
            first = parsed.loans[0]
            period_stmt = insert(ReportingPeriodRow).values(
                accession_number=accession_number,
                beginning_date=first.reporting_period.beginning_date,
                ending_date=first.reporting_period.ending_date,
            )
            period_stmt = period_stmt.on_conflict_do_update(
                index_elements=["accession_number"],
                set_={
                    "beginning_date": period_stmt.excluded.beginning_date,
                    "ending_date": period_stmt.excluded.ending_date,
                },
            )
            self._session.execute(period_stmt)

        loans_written = 0
        properties_written = 0
        for loan in parsed.loans:
            asset_id = self._upsert_asset(
                accession_number=accession_number, loan=loan, source_document_id=source_document_id
            )
            loans_written += 1
            for index, prop in enumerate(loan.properties):
                prop_stmt = insert(PropertySnapshotRow).values(
                    asset_id=asset_id,
                    property_index=index,
                    property_name=prop.property_name,
                    property_address=prop.property_address,
                    property_city=prop.property_city,
                    property_state=prop.property_state,
                    property_zip=prop.property_zip,
                    property_county=prop.property_county,
                    property_type_code=prop.property_type_code,
                    year_built=prop.year_built,
                    net_rentable_square_feet=prop.net_rentable_square_feet,
                    at_securitization=_jsonable(prop.at_securitization),
                    most_recent=_jsonable(prop.most_recent) if prop.most_recent else None,
                    raw_fields=prop.raw_fields,
                )
                prop_stmt = prop_stmt.on_conflict_do_update(
                    index_elements=["asset_id", "property_index"],
                    set_={
                        "property_name": prop_stmt.excluded.property_name,
                        "property_address": prop_stmt.excluded.property_address,
                        "property_city": prop_stmt.excluded.property_city,
                        "property_state": prop_stmt.excluded.property_state,
                        "property_zip": prop_stmt.excluded.property_zip,
                        "property_county": prop_stmt.excluded.property_county,
                        "property_type_code": prop_stmt.excluded.property_type_code,
                        "year_built": prop_stmt.excluded.year_built,
                        "net_rentable_square_feet": prop_stmt.excluded.net_rentable_square_feet,
                        "at_securitization": prop_stmt.excluded.at_securitization,
                        "most_recent": prop_stmt.excluded.most_recent,
                        "raw_fields": prop_stmt.excluded.raw_fields,
                    },
                )
                self._session.execute(prop_stmt)
                properties_written += 1

        for issue in parsed.issues:
            self._session.add(
                DataQualityIssueRow(
                    accession_number=accession_number,
                    asset_number=issue.asset_number,
                    field_name=issue.field_name,
                    message=issue.message,
                    raw_value=issue.raw_value,
                    created_at=datetime.now(UTC),
                )
            )

        return loans_written, properties_written

    def _upsert_asset(
        self, *, accession_number: str, loan: Loan, source_document_id: int | None
    ) -> int:
        stmt = insert(AssetRow).values(
            accession_number=accession_number,
            asset_number=loan.asset_number,
            group_id=loan.group_id,
            originator_name=loan.originator_name,
            origination_date=loan.origination_date,
            original_loan_amount=loan.original_loan_amount,
            original_interest_rate_percentage=loan.original_interest_rate_percentage,
            maturity_date=loan.maturity_date,
            paid_through_date=loan.paid_through_date,
            scheduled_principal_amount=loan.scheduled_principal_amount,
            scheduled_interest_amount=loan.scheduled_interest_amount,
            actual_balance_amount=loan.actual_balance_amount,
            scheduled_balance_amount=loan.scheduled_balance_amount,
            payment_status_code=loan.payment_status_code,
            raw_fields=loan.raw_fields,
            source_document_id=source_document_id,
        )
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["accession_number", "asset_number"],
            set_={
                "group_id": stmt.excluded.group_id,
                "originator_name": stmt.excluded.originator_name,
                "origination_date": stmt.excluded.origination_date,
                "original_loan_amount": stmt.excluded.original_loan_amount,
                "original_interest_rate_percentage": (
                    stmt.excluded.original_interest_rate_percentage
                ),
                "maturity_date": stmt.excluded.maturity_date,
                "paid_through_date": stmt.excluded.paid_through_date,
                "scheduled_principal_amount": stmt.excluded.scheduled_principal_amount,
                "scheduled_interest_amount": stmt.excluded.scheduled_interest_amount,
                "actual_balance_amount": stmt.excluded.actual_balance_amount,
                "scheduled_balance_amount": stmt.excluded.scheduled_balance_amount,
                "payment_status_code": stmt.excluded.payment_status_code,
                "raw_fields": stmt.excluded.raw_fields,
                "source_document_id": stmt.excluded.source_document_id,
            },
        ).returning(AssetRow.id)
        result = self._session.execute(upsert_stmt)
        return int(result.scalar_one())

    def count_rows(self) -> dict[str, int]:
        tables = {
            "source_documents": SourceDocumentRow,
            "cmbs_deals": DealRow,
            "cmbs_filings": FilingRow,
            "cmbs_reporting_periods": ReportingPeriodRow,
            "cmbs_assets": AssetRow,
            "cmbs_property_snapshots": PropertySnapshotRow,
            "data_quality_issues": DataQualityIssueRow,
        }
        return {
            name: self._session.execute(select(func.count()).select_from(model)).scalar_one()
            for name, model in tables.items()
        }
