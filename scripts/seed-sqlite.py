import asyncio
import uuid
import hashlib
import bcrypt
import json
import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.infrastructure.models import Base, ModelConfigModel, ApiKeyModel

DATABASE_URL = "sqlite+aiosqlite:///./gateway.db"

async def seed():
    # Delete existing DB file to ensure fresh start
    if os.path.exists("./gateway.db"):
        os.remove("./gateway.db")
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed Models
        models_data = [
            {
                "provider": "openai", "model_name": "gpt-4o", "display_name": "GPT-4o",
                "context_window": 128000, "max_output_tokens": 4096,
                "capabilities": json.dumps(["streaming", "vision", "tools"]),
                "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015, "priority": 10,
            },
            {
                "provider": "anthropic", "model_name": "claude-3-5-sonnet-latest", "display_name": "Claude 3.5 Sonnet",
                "context_window": 200000, "max_output_tokens": 4096,
                "capabilities": json.dumps(["streaming", "vision"]),
                "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015, "priority": 9,
            },
            {
                "provider": "gemini", "model_name": "gemini-1.5-pro", "display_name": "Gemini 1.5 Pro",
                "context_window": 1000000, "max_output_tokens": 8192,
                "capabilities": json.dumps(["streaming", "vision", "tools"]),
                "cost_per_1k_input": 0.00125, "cost_per_1k_output": 0.00375, "priority": 8,
            }
        ]
        
        for data in models_data:
            m = ModelConfigModel(
                id=str(uuid.uuid4()), provider=data["provider"], model_name=data["model_name"],
                display_name=data["display_name"], context_window=data["context_window"],
                max_output_tokens=data["max_output_tokens"], capabilities=data["capabilities"],
                cost_per_1k_input=data["cost_per_1k_input"], cost_per_1k_output=data["cost_per_1k_output"],
                priority=data["priority"],
            )
            session.add(m)

        # Seed Test API Keys
        test_keys = ["lkg_test_123", "lkg_test_key_12345"]
        for raw_key in test_keys:
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            # Use fixed salt for test keys to ensure consistency if needed, but bcrypt handles it
            bcrypt_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(rounds=10)).decode()
            
            test_key = ApiKeyModel(
                id=str(uuid.uuid4()),
                org_id="org_test",
                user_id="user_test",
                name=f"Test Key ({raw_key})",
                key_hash=key_hash,
                bcrypt_hash=bcrypt_hash,
                preview=f"{raw_key[:8]}...",
                is_active=True,
                permissions={
                    "rate_limit_per_minute": 1000,
                    "can_read": True,
                    "can_write": True,
                    "can_manage_keys": True,
                    "isAdmin": True
                },
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(test_key)
            print(f"Added API Key: {raw_key} (hash: {key_hash[:12]}...)")
        
        await session.commit()
    print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
