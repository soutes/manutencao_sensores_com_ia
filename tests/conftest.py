"""Configuração pytest: adiciona src ao path para todos os testes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
