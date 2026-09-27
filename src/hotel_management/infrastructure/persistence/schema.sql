CREATE TABLE IF NOT EXISTS guests (
    id UUID PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY,
    number TEXT NOT NULL UNIQUE,
    room_type TEXT NOT NULL CHECK (room_type IN ('single', 'double', 'suite')),
    nightly_rate NUMERIC(12, 2) NOT NULL CHECK (nightly_rate >= 0),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL CHECK (status IN ('available', 'maintenance'))
);

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY,
    guest_id UUID NOT NULL REFERENCES guests(id),
    room_id UUID NOT NULL REFERENCES rooms(id),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guests INTEGER NOT NULL CHECK (guests > 0),
    nightly_rate NUMERIC(12, 2) NOT NULL CHECK (nightly_rate >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL CHECK (
        status IN ('reserved', 'checked_in', 'checked_out', 'cancelled')
    ),
    created_at DATE NOT NULL,
    CONSTRAINT booking_dates_are_forward CHECK (check_out > check_in)
);

CREATE INDEX IF NOT EXISTS bookings_room_dates_idx
    ON bookings (room_id, check_in, check_out);

CREATE TABLE IF NOT EXISTS domain_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    published_at TIMESTAMPTZ,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    failed_at TIMESTAMPTZ,
    locked_until TIMESTAMPTZ
);

ALTER TABLE domain_events
    ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE domain_events
    ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE domain_events
    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE domain_events
    ADD COLUMN IF NOT EXISTS failed_at TIMESTAMPTZ;
ALTER TABLE domain_events
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS domain_events_pending_idx
    ON domain_events (next_attempt_at, id)
    WHERE published_at IS NULL AND failed_at IS NULL;
