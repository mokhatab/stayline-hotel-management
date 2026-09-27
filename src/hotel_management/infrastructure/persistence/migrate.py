from pathlib import Path

from hotel_management.infrastructure.configuration import PostgresSettings
from hotel_management.infrastructure.persistence.postgres import psycopg_connection_factory


def migrate() -> None:
    settings = PostgresSettings.from_environment()
    connect = psycopg_connection_factory(settings.dsn)
    schema = (Path(__file__).parent / "schema.sql").read_text()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(schema)
            cursor.executemany(
                """
                INSERT INTO rooms (
                    id, number, room_type, nightly_rate, capacity, currency, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (number) DO NOTHING
                """,
                [
                    (
                        "11111111-1111-4111-8111-111111111111",
                        "101",
                        "single",
                        "85.00",
                        1,
                        "USD",
                        "available",
                    ),
                    (
                        "22222222-2222-4222-8222-222222222222",
                        "202",
                        "double",
                        "125.00",
                        2,
                        "USD",
                        "available",
                    ),
                    (
                        "33333333-3333-4333-8333-333333333333",
                        "303",
                        "suite",
                        "220.00",
                        4,
                        "USD",
                        "available",
                    ),
                ],
            )
        connection.commit()
    print("Hotel database schema is up to date.")


if __name__ == "__main__":
    migrate()
