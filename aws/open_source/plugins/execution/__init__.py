"""
Execution simulators for backtesting.

Architecture:
- BaseExecutor: Core execution logic (portfolio updates, position management)
- Simulators wrap BaseExecutor to add costs:
  - RealisticSimulator (default): Adds spread fees for shorts
  - PerfectExecutor: No fees (for comparison)
  - SlippageSimulator: Adds slippage modeling
"""

from .base_executor import BaseExecutor
from .realistic_simulator import RealisticSimulator
from .perfect_executor import PerfectExecutor
from .slippage_simulator import SlippageSimulator

__all__ = [
    'BaseExecutor',        # Core execution engine
    'RealisticSimulator',  # Default (adds spread fees)
    'PerfectExecutor',     # No fees (comparison)
    'SlippageSimulator'    # Adds slippage
]

