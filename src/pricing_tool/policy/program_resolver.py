"""
Program Resolver - Resolves Active_Program_ID based on account context.
"""
from typing import Optional
import pandas as pd
from pathlib import Path

class ProgramResolver:
    """
    Resolves the Active Program ID for an order.
    
    Waterfall precedence:
    1. Direct Account Mapping
    2. Group Mapping
    3. Order Type / Channel Mapping
    4. Fallback: STANDARD
    """
    
    def __init__(self, program_rules_path: Path):
        self.rules_path = program_rules_path
        self.rules_df = pd.DataFrame()
        if self.rules_path.exists():
            self.rules_df = pd.read_csv(self.rules_path, dtype=str)
    
    def resolve_program(self, account_id: str, account_groups: list[str], order_type: Optional[int] = None) -> str:
        """Resolve the active program ID."""
        if self.rules_df.empty:
            return "STANDARD"
        
        # 1. Order Type Match (Global Overrides like Trade-In/Employee)
        if order_type is not None:
            match = self.rules_df[
                (self.rules_df['match_type'] == 'order_type') &
                (self.rules_df['match_value'] == str(order_type))
            ]
            if not match.empty:
                return match.iloc[0]['program_id']

        # 2. Exact Account Match
        match = self.rules_df[
            (self.rules_df['match_type'] == 'account_id') &
            (self.rules_df['match_value'] == str(account_id))
        ]
        if not match.empty:
            return match.iloc[0]['program_id']

        # 3. Group Match
        if account_groups:
            match = self.rules_df[
                (self.rules_df['match_type'] == 'group_id') &
                (self.rules_df['match_value'].isin(account_groups))
            ]
            if not match.empty:
                if 'priority' in match.columns:
                    match = match.sort_values('priority', ascending=False)
                return match.iloc[0]['program_id']

        # 4. Fallback
        return "STANDARD"
