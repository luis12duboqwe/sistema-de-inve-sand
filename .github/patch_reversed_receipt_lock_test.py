from pathlib import Path

path = Path("backend/tests/test_purchase_restock_lock_order_integrity.py")
text = path.read_text()

replacements = [
    (
        "from threading import Barrier, Event, Lock, get_ident\n",
        "from threading import Barrier, BrokenBarrierError, Event, Lock, get_ident\n",
    ),
    (
        '''    start = Barrier(2)\n    legacy_first_stock_barrier = Barrier(2)\n    state_lock = Lock()\n    worker_threads: set[int] = set()\n    product_lock_seen: set[int] = set()\n    first_stock_seen: set[int] = set()\n''',
        '''    start = Barrier(2)\n    first_product_lock_barrier = Barrier(2)\n    legacy_first_stock_barrier = Barrier(2)\n    state_lock = Lock()\n    worker_threads: set[int] = set()\n    expected_product_order = [first_product_id, second_product_id]\n    product_lock_sequences: dict[int, list[int]] = {}\n    completed_product_lock_sequences: list[tuple[int, ...]] = []\n    protocol_violations: list[tuple[int, tuple[int, ...]]] = []\n    first_stock_seen: set[int] = set()\n\n    def _product_id_from_parameters(parameters) -> int | None:\n        if isinstance(parameters, dict):\n            values = parameters.values()\n        elif isinstance(parameters, (tuple, list)):\n            values = parameters\n        else:\n            values = ()\n        expected = {first_product_id, second_product_id}\n        for value in values:\n            if isinstance(value, int) and not isinstance(value, bool) and value in expected:\n                return value\n        return None\n''',
    ),
    (
        '''        if (\n            normalized.startswith("SELECT")\n            and "FROM PRODUCTS" in normalized\n            and "FOR UPDATE" in normalized\n        ):\n            with state_lock:\n                product_lock_seen.add(thread_id)\n            return\n''',
        '''        if (\n            normalized.startswith("SELECT")\n            and "FROM PRODUCTS" in normalized\n            and "FOR UPDATE" in normalized\n        ):\n            product_id = _product_id_from_parameters(parameters)\n            if product_id is None:\n                with state_lock:\n                    protocol_violations.append((thread_id, ()))\n                return\n\n            with state_lock:\n                sequence = product_lock_sequences.setdefault(thread_id, [])\n                sequence.append(product_id)\n                first_product_for_thread = len(sequence) == 1\n\n            if first_product_for_thread:\n                # Wrong implementations that pre-lock reversed payload order can\n                # acquire different first Product rows. Synchronizing after that\n                # first acquisition makes the ensuing cross-lock deterministic.\n                # The correct sorted implementation has both workers contend for\n                # the same first Product, so the leader times out and proceeds.\n                try:\n                    first_product_lock_barrier.wait(timeout=0.75)\n                except BrokenBarrierError:\n                    pass\n            return\n''',
    ),
    (
        '''        with state_lock:\n            legacy_path = thread_id not in product_lock_seen\n            first_for_thread = thread_id not in first_stock_seen\n            if first_for_thread:\n                first_stock_seen.add(thread_id)\n        if legacy_path and first_for_thread:\n''',
        '''        with state_lock:\n            sequence = tuple(product_lock_sequences.get(thread_id, []))\n            complete_protocol = list(sequence) == expected_product_order\n            if not complete_protocol:\n                protocol_violations.append((thread_id, sequence))\n            legacy_path = len(sequence) == 0\n            first_for_thread = thread_id not in first_stock_seen\n            if first_for_thread:\n                first_stock_seen.add(thread_id)\n        if legacy_path and first_for_thread:\n''',
    ),
    (
        '''        finally:\n            with state_lock:\n                worker_threads.discard(thread_id)\n                product_lock_seen.discard(thread_id)\n                first_stock_seen.discard(thread_id)\n            session.close()\n''',
        '''        finally:\n            with state_lock:\n                worker_threads.discard(thread_id)\n                sequence = product_lock_sequences.pop(thread_id, [])\n                completed_product_lock_sequences.append(tuple(sequence))\n                first_stock_seen.discard(thread_id)\n            session.close()\n''',
    ),
    (
        '''    assert sorted(status for status, _ in results) == [200, 200]\n\n    db_session.expire_all()\n    stocks = {\n''',
        '''    assert sorted(status for status, _ in results) == [200, 200]\n    assert protocol_violations == []\n    assert sorted(completed_product_lock_sequences) == sorted(\n        [tuple(expected_product_order), tuple(expected_product_order)]\n    )\n\n    db_session.expire_all()\n    stocks = {\n''',
    ),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one replacement target, found {count}: {old[:80]!r}")
    text = text.replace(old, new, 1)

path.write_text(text)
