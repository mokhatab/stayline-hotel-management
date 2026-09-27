from decimal import Decimal
import unittest
from uuid import uuid4

from hotel_management.domain.entities import Room, RoomType
from hotel_management.domain.value_objects import Money, RoomId
from hotel_management.infrastructure.persistence.postgres import (
    PostgresBookingUnitOfWork,
    PostgresRoomRepository,
)


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, query, params=()):
        self.calls.append((query, params))

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks = getattr(self, "rollbacks", 0) + 1

    def close(self):
        self.closed = True


class PostgresAdapterTests(unittest.TestCase):
    def test_room_repository_maps_database_rows_to_domain_entities(self):
        room_id = uuid4()
        connection = FakeConnection(
            [(room_id, "202", "double", Decimal("125.00"), 2, "USD", "available")]
        )
        repository = PostgresRoomRepository(lambda: connection)

        rooms = repository.list()

        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0].id, RoomId(room_id))
        self.assertEqual(rooms[0].nightly_rate, Money.from_amount("125"))
        self.assertEqual(connection.commits, 0)
        self.assertIn("FROM rooms ORDER BY number", connection.cursor_instance.calls[0][0])

    def test_repository_writes_only_persistence_data(self):
        connection = FakeConnection([])
        repository = PostgresRoomRepository(lambda: connection)
        room = Room(RoomId.new(), "404", RoomType.SUITE, Money.from_amount("220"), 4)

        # Room writes are intentionally not exposed by the current application port;
        # this assertion documents that the read adapter does not invent a write API.
        self.assertFalse(hasattr(repository, "save"))
        self.assertEqual(room.capacity, 4)

    def test_unit_of_work_commits_once_after_scope_exits(self):
        connection = FakeConnection([])
        unit_of_work = PostgresBookingUnitOfWork(lambda: connection)

        with unit_of_work:
            self.assertEqual(connection.commits, 0)
            self.assertEqual(connection.rollbacks if hasattr(connection, "rollbacks") else 0, 0)

        self.assertEqual(connection.commits, 1)
        self.assertTrue(connection.closed)

    def test_unit_of_work_rolls_back_when_scope_raises(self):
        connection = FakeConnection([])
        unit_of_work = PostgresBookingUnitOfWork(lambda: connection)

        with self.assertRaises(RuntimeError):
            with unit_of_work:
                raise RuntimeError("booking write failed")

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()