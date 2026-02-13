import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.audit import AuditLogger
from app.application.services.cost_tracker import CostTrackerService
from app.infrastructure.models import Base, AuditLogModel
from app.api.middleware.compliance import ComplianceMiddleware

# Mock Redis for verification
class MockRedis:
    def __init__(self):
        self.data = {}
        self.commands = []
    
    async def get(self, key): 
        val = self.data.get(key)
        return val if val else None
        
    async def set(self, key, val, ex=None): 
        self.data[key] = str(val).encode()

    def incrbyfloat(self, key, val):
        self.commands.append(("incrbyfloat", key, val))
        return self

    def incrby(self, key, val):
        self.commands.append(("incrby", key, val))
        return self

    def expire(self, key, val):
        self.commands.append(("expire", key, val))
        return self

    def pipeline(self): return self
    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass

    async def execute(self):
        for cmd, key, val in self.commands:
            if cmd == "incrbyfloat":
                curr = float(self.data.get(key, b"0").decode())
                self.data[key] = str(curr + val).encode()
            elif cmd == "incrby":
                curr = int(self.data.get(key, b"0").decode())
                self.data[key] = str(curr + val).encode()
            # ignore expire for mock
        self.commands = []

async def verify_enterprise_features():
    print("🔍 Starting Enterprise Features Verification...")
    
    # Setup in-memory DB for test
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Verify Audit Logger (Tamper-evident chain)
    audit_logger = AuditLogger(async_session)
    print("📝 Generating audit entries...")
    for i in range(5):
        await audit_logger.log(
            event_type="test_event",
            actor_id="admin_user",
            target_id=str(uuid.uuid4()),
            target_type="model",
            payload={"action": f"update_{i}", "api_key": "lkg_secret_123"}
        )
    
    # Check for PII redaction
    async with async_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(AuditLogModel).limit(1))
        entry = res.scalar_one()
        print(f"✅ PII Redaction Check: {entry.payload['api_key']}")
        assert entry.payload['api_key'] == "[REDACTED]"

    print("🛡️ Verifying audit chain integrity...")
    is_valid = await audit_logger.verify_chain()
    print(f"✅ Audit Chain Valid: {is_valid}")
    assert is_valid is True

    # 2. Verify Cost Tracker
    redis = MockRedis()
    cost_tracker = CostTrackerService(redis, async_session)
    
    print("💰 Tracking usage...")
    await cost_tracker.track_usage(
        org_id="org_1",
        user_id="user_1",
        model="gpt-4o",
        provider="openai",
        cost=Decimal("0.05"),
        tokens=1000
    )
    
    status = await cost_tracker.get_org_status("org_1")
    print(f"✅ Budget Status: Spend=${status.current_spend}, Limit=${status.limit}")
    assert status.current_spend == Decimal("0.05")

    # 3. Verify Compliance Middleware Patterns
    middleware = ComplianceMiddleware(None)
    pii_text = "My email is test@example.com and key is lkg_12345678901234567890123456789012"
    redacted = middleware.redact_pii(pii_text)
    print(f"✅ Regex Redaction: {redacted}")
    assert "[EMAIL_REDACTED]" in redacted

    print("\n🎉 All Enterprise Features Verified Successfully!")

if __name__ == "__main__":
    asyncio.run(verify_enterprise_features())
