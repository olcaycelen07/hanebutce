CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS households (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    owner_user_id BIGINT NOT NULL REFERENCES users(id),
    plan_type TEXT NOT NULL DEFAULT 'free',
    currency_code TEXT NOT NULL DEFAULT 'TRY',
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS household_members (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    joined_at TIMESTAMP NOT NULL,
    UNIQUE (household_id, user_id)
);

CREATE TABLE IF NOT EXISTS household_categories (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    UNIQUE (household_id, type, name)
);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    created_by_user_id BIGINT NOT NULL REFERENCES users(id),
    member_user_id BIGINT NOT NULL REFERENCES users(id),
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    category TEXT NOT NULL,
    transaction_date DATE NOT NULL,
    note TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS bills (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    created_by_user_id BIGINT NOT NULL REFERENCES users(id),
    member_user_id BIGINT NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    category TEXT NOT NULL DEFAULT 'Genel',
    due_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    frequency TEXT NOT NULL DEFAULT 'one_time',
    last_generated_date DATE,
    note TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS invitations (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    invited_by_user_id BIGINT NOT NULL REFERENCES users(id),
    accepted_by_user_id BIGINT REFERENCES users(id),
    created_at TIMESTAMP NOT NULL,
    accepted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_household_members_household_id ON household_members (household_id);
CREATE INDEX IF NOT EXISTS idx_transactions_household_id_date ON transactions (household_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_bills_household_id_due_date ON bills (household_id, due_date);
CREATE INDEX IF NOT EXISTS idx_invitations_household_id_status ON invitations (household_id, status);
