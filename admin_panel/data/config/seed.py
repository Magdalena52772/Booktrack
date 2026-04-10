"""Konfiguracja SEED i Fakera dla powtarzalnej symulacji"""

import random

# ============== POWTARZALNOŚĆ SYMULACJI ==============
# Zapewnia powtarzalne wyniki przy każdym uruchomieniu
SEED = 52772
random.seed(SEED)

_fake_instance = None

def get_fake():
    """Zwraca instancję Fakera tylko gdy jest potrzebna (Lazy Loading)."""
    global _fake_instance
    if _fake_instance is None:
        from faker import Faker
        _fake_instance = Faker("pl_PL")
        _fake_instance.seed_instance(SEED)
    return _fake_instance