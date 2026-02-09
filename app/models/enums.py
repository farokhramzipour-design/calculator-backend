from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    IMPORT_UK = "IMPORT_UK"
    IMPORT_EU = "IMPORT_EU"
    EXPORT_UK = "EXPORT_UK"
    EXPORT_EU = "EXPORT_EU"


class ShipmentStatus(str, Enum):
    DRAFT = "DRAFT"
    NEEDS_INPUT = "NEEDS_INPUT"
    READY = "READY"
    CALCULATED = "CALCULATED"


class Incoterm(str, Enum):
    EXW = "EXW"
    FOB = "FOB"
    CIF = "CIF"
    CFR = "CFR"
    DDP = "DDP"
    FCA = "FCA"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"


class ProviderType(str, Enum):
    UK_TARIFF = "UK_TARIFF"
    EU_TARIC = "EU_TARIC"
    VAT = "VAT"
    FX = "FX"
