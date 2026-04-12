# 🔴 Issues to Fix - Test Output Summary

Data: 2026-04-12  
Status: ACTIVE BUGS

---

## 1. ❌ PPD Calculation Mismatch (test_users_view_flow.py)

### Issue
UI pokazuje błędne wartości PPD dla niektórych użytkowników. Wartości są niedoszacowane.

### Failing Users
- **piotrstempniak520**: UI(18.1) vs Real(51.3) | **Błąd: +33.2**
- **mieszkopopielarczyk272**: UI(22.1) vs Real(66.7) | **Błąd: +44.6**

### Root Cause
Prawdopodobnie błędne filtrowanie lub agregacja w `get_all()` lub `get_detailed_user_profile()` w UserRepository

### Files Involved
- `data/repositories/user_repo.py` - sprawdzić logikę PPD
- `views/users_view.py` - weryfikacja wyświetlania

### Fix Priority
🔥 **HIGH** - Podstawowy błąd w kalkulacji metryki

---

## 2. ❌ Active PPD = 0 for Active Users (test_04)

### Issue
Szczegółowy profil użytkownika (ID 1000) pokazuje `active_ppd = 0` mimo że powinno być `18.0`

### Expected vs Actual
- Expected: 18.0
- Got: 0

### Root Cause
`get_detailed_user_profile()` nie oblicza prawidłowo PPD dla aktywnych użytkowników

### Files Involved
- `data/repositories/user_repo.py:get_detailed_user_profile()`
- Prawdopodobnie brak obsługi dla activity data

### Fix Priority
🔥 **HIGH** - Wpływa na panel detali

---

## 3. ❌ SQL Syntax Error: "near AND" (activity_repo.py)

### Issue
Błąd w `get_activity_kpi()` dla filtrów czasowych

```
sqlite3.OperationalError: near "AND": syntax error
```

### Affected Filters
- `week` (0.4736s)
- `month` (2.0481s)
- `year` (5.2846s)

### Root Cause
`date_clause` z `TimeFilterService` nie zawiera `WHERE` - zwraca tylko `AND timestamp >= ?`  
Kiedy łączy się z SQL: `FROM activity AND timestamp >= ?` → brak WHERE

### Files Involved
- `data/repositories/activity_repo.py:18` - query construction
- `data/services/time_filter_service.py` - format warunku

### Fix Priority
🔥 **CRITICAL** - Uniemożliwia działanie filtrów czasowych

### Solution
`activity_repo.py` musi konstruować WHERE prawidłowo, podobnie jak `statistics_repo.py` robi to:
```python
where_clause = f"WHERE 1=1 {condition}" if condition else ""
```

---

## 4. ❌ ModuleNotFoundError (perf_profiler_diag.py)

### Issue
```
ModuleNotFoundError: No module named 'data'
```

### Root Cause
Script uruchamiany z innego katalogu - PATH issue

### Files Involved
- `tests/performance/perf_profiler_diag.py:12`

### Fix Priority
⚠️ **MEDIUM** - Diagnostyka, nie core feature

### Solution
Dodać path configuration z `sys.path.insert()` jak w innych testach

---

## 5. ⚠️ Performance Issues

### Dashboard
- **Status**: FAIL
- **Time**: 3.8373s
- **Issue**: Wymaga optymalizacji
- **Root Cause**: Prawdopodobnie zbyt wiele SQL queries

### Reports
- **Status**: FAIL  
- **Time**: 1.0600s
- **Issue**: Wymaga optymalizacji

### All Modules - Lag Detected
- Dashboard: 90.39ms max, 75.05ms avg
- Users: 85.65ms max, 81.80ms avg
- Activity: 96.05ms max, 91.20ms avg
- **Status**: Dostrzegalny lag dla użytkownika

### Startup Performance
- **Issue**: "Mega chujowo" (very bad)
- **Root Cause**: Inicjalizacja w `main.py` - prawdopodobnie synchro zapytania SQL bez batch processing

### Fix Priority
⚠️ **MEDIUM** - UX issue, nie blocker

---

## Summary Table

| Test | Status | Priority | File |
|------|--------|----------|------|
| PPD Mismatch (18.1 vs 51.3) | FAIL | 🔥 HIGH | user_repo.py |
| Active PPD = 0 | FAIL | 🔥 HIGH | user_repo.py |
| SQL "near AND" error | FAIL | 🔥 CRITICAL | activity_repo.py |
| ModuleNotFoundError | FAIL | ⚠️ MEDIUM | perf_profiler_diag.py |
| Dashboard Performance | WARN | ⚠️ MEDIUM | dashboard_view.py |
| Lag in UI | WARN | ⚠️ MEDIUM | main.py |

---

## Next Steps

1. **FIRST**: Naprawić activity_repo.py WHERE clause (blocker)
2. **SECOND**: Debugować PPD calculation w user_repo.py (2x HIGH priority)
3. **THIRD**: Dodać PATH fix do perf_profiler_diag.py
4. **FOURTH**: Optymalizacja performance (dashboard/reports)

