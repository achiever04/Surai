"""
Migration: Change action_timestamp from TIMESTAMP to TIMESTAMPTZ
"""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        "postgresql://surveillance_user:secure_password_123@localhost:5432/surveillance_db"
    )
    await conn.execute(
        "ALTER TABLE detections ALTER COLUMN action_timestamp TYPE TIMESTAMPTZ USING action_timestamp AT TIME ZONE 'UTC'"
    )
    print("Migration successful: action_timestamp -> TIMESTAMPTZ")
    await conn.close()

asyncio.run(main())
