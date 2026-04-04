#!/usr/bin/env python3
"""
Seed script for Auxilia database.
Run this once to populate zones and sample data.

Usage:
    python seed.py
"""
import asyncio
import uuid
import random
from datetime import datetime, timedelta

from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.database import Zone, Rider, Policy, Claim, TriggerEvent
from app.models.database import PersonaType, RiderStatus, PolicyStatus, ClaimStatus, TriggerType
from app.agents.trigger_agent import ZONE_CONFIG
from sqlalchemy import select


async def seed_zones():
    """Seed zones from ZONE_CONFIG."""
    async with AsyncSessionLocal() as db:
        created = 0
        zone_ids = []
        
        for zone_id, zone_config in ZONE_CONFIG.items():
            zone_ids.append(zone_id)
            # Check if exists
            existing = await db.execute(
                select(Zone).where(Zone.id == zone_id)
            )
            if existing.scalar_one_or_none():
                print(f"  Zone '{zone_id}' already exists")
                continue
            
            # Create zone
            zone = Zone(
                id=zone_id,
                name=zone_config["name"],
                city=zone_config["city"],
                state="",
                country="IN",
                latitude=zone_config["lat"],
                longitude=zone_config["lon"],
                radius_km=5.0,
                risk_level="medium",
                base_premium_factor=1.0,
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(zone)
            created += 1
            print(f"  Created zone: {zone_id} ({zone_config['name']}, {zone_config['city']})")
        
        await db.commit()
        return created, zone_ids

async def seed_mock_data(zone_ids):
    """Seed mock riders, policies, and claims."""
    async with AsyncSessionLocal() as db:
        # Check if riders already exist
        existing = await db.execute(select(Rider).limit(1))
        if existing.scalar_one_or_none():
            print("  Mock data already exists, skipping")
            return

        print("  Generating mock riders...")
        riders = []
        names = ["Amit Kumar", "Priya Singh", "Rahul Sharma", "Sneha Gupta", "Vikram Patel", "Anita Desai", "Rajesh Verma", "Neha Joshi", "Suresh Nair", "Kavita Reddy"]
        age_bands = ["18-21", "22-25", "26-35", "36-45"]
        vehicle_types = ["bike", "scooter", "ev_scooter"]
        shift_types = ["lunch", "evening", "late_night", "mixed"]
        for i, name in enumerate(names):
            rider = Rider(
                id=str(uuid.uuid4()),
                name=name,
                phone=f"+9198765432{i:02d}",
                password_hash=hash_password("rider123"),
                email=f"rider{i}@example.com",
                persona=random.choice(list(PersonaType)),
                zone_id=random.choice(zone_ids),
                age_band=random.choice(age_bands),
                vehicle_type=random.choice(vehicle_types),
                shift_type=random.choice(shift_types),
                tenure_months=random.randint(1, 48),
                latitude=12.9716 + random.uniform(-0.05, 0.05),
                longitude=77.5946 + random.uniform(-0.05, 0.05),
                risk_score=random.uniform(0.1, 0.9),
                status=RiderStatus.ACTIVE,
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 180))
            )
            db.add(rider)
            riders.append(rider)
        
        await db.commit()
        
        print("  Generating mock policies...")
        policies = []
        for rider in riders:
            # Create 1-2 policies per rider
            for j in range(random.randint(1, 2)):
                is_active = j == 0  # First policy is active, second might be expired
                start_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                if not is_active:
                    start_date = start_date - timedelta(days=60)
                end_date = start_date + timedelta(days=30)
                status = PolicyStatus.ACTIVE if end_date > datetime.utcnow() else PolicyStatus.EXPIRED

                policy = Policy(
                    id=str(uuid.uuid4()),
                    rider_id=rider.id,
                    zone_id=rider.zone_id,
                    persona=rider.persona,
                    premium=random.uniform(100, 500),
                    coverage=random.uniform(5000, 20000),
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    created_at=start_date
                )
                db.add(policy)
                policies.append(policy)
                
        await db.commit()
        
        print("  Generating mock claims...")
        for policy in policies:
            # 30% chance of a claim
            if random.random() < 0.3:
                claim_status = random.choice([ClaimStatus.PAID, ClaimStatus.APPROVED, ClaimStatus.PENDING, ClaimStatus.REJECTED])
                trigger_type = random.choice(list(TriggerType))
                
                claim = Claim(
                    id=str(uuid.uuid4()),
                    policy_id=policy.id,
                    rider_id=policy.rider_id,
                    trigger_type=trigger_type,
                    trigger_value=random.uniform(50, 150),
                    threshold=random.uniform(40, 100),
                    amount=random.uniform(500, policy.coverage * 0.5),
                    status=claim_status,
                    fraud_score=random.uniform(0, 0.4),
                    ai_decision="Approved by AI" if claim_status in [ClaimStatus.PAID, ClaimStatus.APPROVED] else "Flagged for manual review",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 10)),
                    processed_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)) if claim_status in [ClaimStatus.PAID, ClaimStatus.APPROVED, ClaimStatus.REJECTED] else None
                )
                db.add(claim)
        
        await db.commit()
        print("  Mock data seeded successfully!")

async def main():
    print("=" * 50)
    print("Auxilia Database Seeder")
    print("=" * 50)
    
    # Create tables
    print("\n[1/3] Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  Done!")
    
    # Seed zones
    print(f"\n[2/3] Seeding {len(ZONE_CONFIG)} zones...")
    created, zone_ids = await seed_zones()
    print(f"  Created {created} new zones")
    
    # Seed mock data
    print("\n[3/3] Seeding mock riders, policies, and claims...")
    if zone_ids:
        await seed_mock_data(zone_ids)
    
    print("\n" + "=" * 50)
    print("Seeding complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
