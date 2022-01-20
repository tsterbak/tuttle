"""Object model."""

import datetime
import hashlib
import uuid

from typing import Optional, List
from pydantic import constr

import sqlalchemy
from sqlmodel import Field, Relationship
from sqlmodel import SQLModel
from pydantic import EmailStr
from decimal import Decimal

# TODO: support currencies
# from money.money import Money
# from money.currency import Currency

from .time import Cycle, TimeUnit

# TODO: created & modified time stamps


def OneToOneRelationship(back_populates):
    return Relationship(
        back_populates=back_populates,
        sa_relationship_kwargs={"uselist": False},
    )


class Entity(SQLModel):
    """Abstract base class?"""

    id: Optional[int] = Field(default=None, primary_key=True)
    time_created: datetime.datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
        )
    )
    time_modified: datetime.datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
        )
    )


class Address(SQLModel, table=True):
    """Postal address."""

    id: Optional[int] = Field(default=None, primary_key=True)
    street: str
    number: str
    city: str
    postal_code: str
    country: str
    users: List["User"] = Relationship(back_populates="address")
    contacts: List["Contact"] = Relationship(back_populates="address")


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    subtitle: str
    e_mail: EmailStr
    address_id: Optional[int] = Field(default=None, foreign_key="address.id")
    address: Optional[Address] = Relationship(back_populates="users")
    VAT_number: Optional[str]
    # business_account_id: Optional[int] = Field(default=None, foreign_key="bankaccount.id")
    # business_account: Optional["BankAccount"]
    icloud_account_id: Optional[int] = Field(
        default=None, foreign_key="icloudaccount.id"
    )
    icloud_account: Optional["ICloudAccount"] = Relationship(back_populates="user")


class ICloudAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_name: str
    user: User = OneToOneRelationship(back_populates="icloud_account")


class Bank(SQLModel, table=True):
    """A bank."""

    id: Optional[int] = Field(default=None, primary_key=True)
    BLZ: str  # TODO: add type / validator


class BankAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    IBAN: str  # TODO: add type / validator
    BIC: str  # TODO: add type / validator
    username: str  # online banking user name
    # owner: User


class Contact(SQLModel, table=True):
    """An entry in the address book."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    e_mail: Optional[EmailStr]
    address_id: Optional[int] = Field(default=None, foreign_key="address.id")
    address: Optional[Address] = Relationship(back_populates="contacts")
    invoicing_contact_of: List["Client"] = Relationship(
        back_populates="invoicing_contact"
    )
    # post address


class Client(SQLModel, table=True):
    """A client the freelancer has contracted with."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # Client 1:1 invoicing Contact
    invoicing_contact_id: int = Field(default=None, foreign_key="contact.id")
    invoicing_contact: Contact = Relationship(back_populates="invoicing_contact_of")
    contracts: List["Contract"] = Relationship(back_populates="client")
    # non-invoice related contact person?


# class Rate(SQLModel, table=True):
#     """Contractual rate."""
#     id: Optional[int] = Field(default=None, primary_key=True)
#     amount: Decimal
#     unit: TimeUnit = Field(
#         sa_column=sqlalchemy.Column(sqlalchemy.Enum(TimeUnit))
#     )
#     # currency: Currency  # TODO:
#     contracts: List["Contract"] = Relationship(back_populates="rate")


class Contract(SQLModel, table=True):
    """A contract defines the business conditions of a project"""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    date: datetime.date
    # Contract n:1 Client
    client_id: Optional[int] = Field(default=None, foreign_key="client.id")
    client: Client = Relationship(back_populates="contracts")
    rate: Decimal
    currency: str  # TODO: currency representation
    unit: TimeUnit = Field(sa_column=sqlalchemy.Column(sqlalchemy.Enum(TimeUnit)))
    volume: int
    billing_cycle: Cycle = Field(sa_column=sqlalchemy.Column(sqlalchemy.Enum(Cycle)))
    projects: List["Project"] = Relationship(back_populates="contract")
    invoices: List["Invoice"] = Relationship(back_populates="contract")


class Project(SQLModel, table=True):
    """A project is a group of contract work for a client."""

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    tag: constr(regex=r"#\S+")
    start_date: datetime.date
    end_date: datetime.date
    # Project m:n Contract
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    contract: Contract = Relationship(back_populates="projects")
    # Project 1:n Timesheet
    timesheets: List["Timesheet"] = Relationship(back_populates="project")
    # volume
    volume: Optional[int]  # TODO: project volume


class Timesheet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Timesheet n:1 Project
    project_id: Optional[int] = Field(default=None, foreign_key="project.id")
    project: Project = Relationship(back_populates="timesheets")
    invoice: "Invoice" = Relationship(back_populates="timesheet")

    # period: str
    # client: str
    # comment: str


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: Optional[str]
    # date and time
    date: datetime.date
    due_date: datetime.date
    sent_date: datetime.date
    # Invoice 1:n Timesheet
    timesheet_id: Optional[int] = Field(default=None, foreign_key="timesheet.id")
    timesheet: Timesheet = Relationship(back_populates="invoice")
    # Invoice n:1 Contract
    contract_id: Optional[int] = Field(default=None, foreign_key="contract.id")
    contract: Contract = Relationship(back_populates="invoices")
    # status
    sent: bool
    paid: bool
    cancelled: bool
    # payment: Optional["Payment"] = Relationship(back_populates="invoice")
    # invoice items
    items: List["InvoiceItem"] = Relationship(back_populates="invoice")

    #
    @property
    def sum(self) -> Decimal:
        """Sum over all invoice items."""
        return sum(item.sum for item in self.items)

    @property
    def VAT_total(self) -> Decimal:
        """Sum of VAT over all invoice items."""
        return sum(item.VAT for item in self.items)

    @property
    def total(self) -> Decimal:
        """Total invoiced amount."""
        return self.sum + self.VAT_total

    def generate_number(self):
        """Generate an invoice number"""
        date_prefix = self.date.strftime("%Y-%m-%d")
        hash_suffix = hashlib.shake_256(str(uuid.uuid4()).encode("utf-8")).hexdigest(2)
        self.number = f"{date_prefix}-{hash_suffix}"


class InvoiceItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # date and time
    date: datetime.date
    #
    amount: int
    unit: str
    unit_price: Decimal
    description: str
    VAT_rate: Decimal
    # invoice
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    invoice: Invoice = Relationship(back_populates="items")

    @property
    def sum(self) -> Decimal:
        """."""
        return self.amount * self.unit_price

    @property
    def VAT(self) -> Decimal:
        """VAT for the invoice item."""
        return self.sum * self.VAT_rate


# class Payment(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     # invoice: Invoice = Relationship(back_populates="payment")


class Cycle:
    pass

    # TODO: monthly, quarterly, yearly...


class Tax:
    country: str
    cycle: Cycle


class ValueAddedTax(Tax):
    """Value added tax."""

    pass


class IncomeTax(Tax):
    """Income tax."""

    pass


class TimelineItem(SQLModel, table=True):
    """An item that appears in the freelancer's timeline."""

    id: Optional[int] = Field(default=None, primary_key=True)
    time: datetime.datetime = Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
        )
    )
    content: str
