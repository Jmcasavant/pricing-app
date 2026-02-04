"""
Centralized settings and path configuration for the pricing tool.
"""
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def get_project_root() -> Path:
    """Get the project root directory (where app.py lives)."""
    # Walk up from this file to find the project root
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'Master_Catalog_Final.csv').exists() or (parent / 'app.py').exists():
            return parent
    # Fallback to 3 levels up from this file
    return Path(__file__).resolve().parent.parent.parent.parent


@dataclass
class Settings:
    """Application settings with sensible defaults."""
    
    # Project paths
    project_root: Path
    
    # Input files
    shopify_export: Path
    rules_excel: Path
    
    # Tier price list files (discovered dynamically)
    tier_files: dict[str, Path]
    
    # Output files
    master_catalog: Path
    build_report: Path
    
    # Rule files (Phase 2)
    rules_csv: Optional[Path] = None
    compiled_rules: Optional[Path] = None
    
    # Active tiers
    active_tiers: tuple = ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM')
    
    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> 'Settings':
        """Load settings from the project structure."""
        root = project_root or get_project_root()
        
        # Discover tier files
        tier_files = {}
        for tier in ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM'):
            tier_path = root / f'{tier}.csv'
            if tier_path.exists():
                tier_files[tier] = tier_path
        
        return cls(
            project_root=root,
            shopify_export=root / 'products_export_1.csv',
            rules_excel=root / 'Pricing Rules Starter 1.xlsx',
            tier_files=tier_files,
            master_catalog=root / 'Master_Catalog_Final.csv',
            build_report=root / 'src' / 'pricing_tool' / 'data' / 'outputs' / 'build_report.json',
            rules_csv=root / 'src' / 'pricing_tool' / 'rules' / 'rules.csv',
            compiled_rules=root / 'src' / 'pricing_tool' / 'rules' / 'compiled_rules.json',
        )


# Default settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings
