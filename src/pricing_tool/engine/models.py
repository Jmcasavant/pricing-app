"""
Data models for the pricing engine.

Uses dataclasses for structured, type-safe data representation.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TraceStep:
    """A single step in the pricing resolution trace."""
    step: str
    description: str
    value: Optional[str] = None


@dataclass
class LineItem:
    """A single line item in a quote result."""
    sku: str
    description: str
    quantity: int
    unit_price: float
    extended_price: float
    tier_used: str
    source: str  # "Contract" or "MSRP"
    rules_applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    configuration: Optional[dict[str, str]] = None
    trace: list[TraceStep] = field(default_factory=list)
    
    def add_trace(self, step: str, description: str, value: str = None):
        """Add a step to the trace for this line item."""
        self.trace.append(TraceStep(step=step, description=description, value=value))
    
    def add_warning(self, warning: str):
        """Add a warning for this line item."""
        self.warnings.append(warning)
    
    def get_trace_text(self) -> str:
        """Get human-readable trace as formatted text."""
        lines = []
        for t in self.trace:
            if t.value:
                lines.append(f"→ {t.step}: {t.description} = {t.value}")
            else:
                lines.append(f"→ {t.step}: {t.description}")
        return "\n".join(lines)


@dataclass
class Request:
    """A pricing request with account context and items."""
    account_id: str
    items: dict[str, int]  # SKU → quantity
    
    # Optional line configuration for customizable items (e.g., helmets)
    # Map of SKU -> { "shell_color": "matte_black", ... }
    item_configs: Optional[dict[str, dict[str, str]]] = None
    
    # Optional context for rule matching and policy resolution
    channel: Optional[str] = None  # "phone", "email", "portal"
    request_date: Optional[str] = None  # ISO date string
    
    # [NEW] Phase 1 Context
    order_date: Optional[str] = None
    payment_method: Optional[str] = None  # PO/CC
    order_type: Optional[int] = None
    ship_method: Optional[str] = None
    ship_to_type: Optional[str] = None
    customer_tier: Optional[str] = None


@dataclass
class Result:
    """Complete result of a pricing calculation."""
    account_id: str
    tier: str
    total: float
    lines: list[LineItem]
    intel: dict = field(default_factory=dict)
    policy: dict = field(default_factory=dict)  # [NEW] Terms/Freight/Holds
    warnings: list[str] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    
    # Metadata
    catalog_hash: Optional[str] = None
    rules_hash: Optional[str] = None
    
    def add_trace(self, step: str, description: str, value: str = None):
        """Add a step to the result-level trace."""
        self.trace.append(TraceStep(step=step, description=description, value=value))
    
    def add_warning(self, warning: str):
        """Add a result-level warning."""
        self.warnings.append(warning)
    
    def get_trace_text(self) -> str:
        """Get human-readable result trace as formatted text."""
        lines = []
        for t in self.trace:
            if t.value:
                lines.append(f"• {t.step}: {t.description} = {t.value}")
            else:
                lines.append(f"• {t.step}: {t.description}")
        return "\n".join(lines)
    
    def to_legacy_dict(self) -> dict:
        """Convert to legacy dict format for backward compatibility."""
        return {
            "Account": self.account_id,
            "Tier": self.tier,
            "Total": self.total,
            "Lines": [
                {
                    "SKU": line.sku,
                    "Description": line.description,
                    "Quantity": line.quantity,
                    "Unit Price": line.unit_price,
                    "Total": line.extended_price,
                    "Source": line.source,
                }
                for line in self.lines
            ]
        }
