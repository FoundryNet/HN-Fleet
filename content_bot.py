#!/usr/bin/env python3
"""
FoundryNet Content Collector Bot
Monitors Hacker News, collects top stories, earns MINT for work
Part of autonomous fleet (Collector → Processor → Decision)
"""

import json
import base58
import nacl.signing
import requests
import datetime
import time
from pathlib import Path
import hashlib
import uuid
import random
import logging
import os

# -----------------------
# SETUP
# -----------------------
API_URL = "https://lsijwmklicmqtuqxhgnu.supabase.co/functions/v1/main-ts"
CREDENTIALS_FILE = Path(os.path.expanduser("~/.foundry_collector_bot_credentials.json"))
STORIES_LOG_FILE = Path(os.path.expanduser("~/.foundry_collector_bot_stories.json"))
EARNINGS_LOG_FILE = Path(os.path.expanduser("~/.foundry_collector_bot_earnings.json"))
FLEET_LOG_FILE = Path(os.path.expanduser("~/.foundry_fleet_events.json"))

RECIPIENT_WALLET = "EeeRgLhQWttphogcBpbHNGNxdx2hzYgS6nakVnLAJZrk"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[FoundryNet %(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger(__name__)

# HN API
HN_API = "https://hacker-news.firebaseio.com/v0"

# -----------------------
# MACHINE ID
# -----------------------
def load_or_create_machine():
    """Load existing or create new machine credentials"""
    if CREDENTIALS_FILE.exists():
        creds = json.load(open(CREDENTIALS_FILE))
        logger.info(f"✅ Loaded existing collector bot identity: {creds['machine_uuid']}")
        return creds
    else:
        machine_uuid = str(uuid.uuid4())
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        creds = {
            "machine_uuid": machine_uuid,
            "public_key": base58.b58encode(bytes(verify_key)).decode(),
            "secret_key": base58.b58encode(bytes(signing_key)).decode()
        }
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds, f, indent=2)
        logger.info(f"🆕 Generated new collector bot identity: {machine_uuid}")
        print(f"✅ Collector Bot Connected to FoundryNet.")
        print(f"Machine ID: {json.dumps(creds, indent=2)}")
        return creds

def register_machine(creds):
    """Register bot with FoundryNet"""
    payload = {
        "machine_uuid": creds["machine_uuid"],
        "machine_pubkey_base58": creds["public_key"],
        "metadata": {
            "os": "content_collector",
            "version": "1.0.0",
            "purpose": "hacker_news_aggregation"
        }
    }
    try:
        r = requests.post(f"{API_URL}/register-machine", json=payload, timeout=10)
        if r.ok:
            logger.info("Machine registered with FoundryNet")
            return True
        else:
            logger.error(f"Machine registration failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return False

# -----------------------
# HN COLLECTION
# -----------------------
def fetch_top_stories(limit=20):
    """Fetch top stories from HN"""
    try:
        # Get top story IDs
        r = requests.get(f"{HN_API}/topstories.json", timeout=5)
        if r.status_code != 200:
            logger.warning(f"Failed to fetch top story IDs: {r.status_code}")
            return []
        
        story_ids = r.json()[:limit]
        
        # Fetch each story
        stories = []
        for story_id in story_ids:
            try:
                story_r = requests.get(f"{HN_API}/item/{story_id}.json", timeout=3)
                if story_r.status_code == 200:
                    story = story_r.json()
                    # Only include stories with required fields
                    if story.get("type") == "story" and story.get("title"):
                        stories.append({
                            "id": story_id,
                            "title": story.get("title"),
                            "url": story.get("url", ""),
                            "score": story.get("score", 0),
                            "by": story.get("by", "unknown"),
                            "descendants": story.get("descendants", 0),
                            "time": story.get("time", 0)
                        })
            except Exception as e:
                logger.debug(f"Failed to fetch story {story_id}: {e}")
                continue
        
        logger.info(f"✅ Collected {len(stories)} top stories from HN")
        return stories
    
    except Exception as e:
        logger.error(f"HN fetch failed: {e}")
        return []

def log_stories(stories):
    """Log collected stories to persistent storage"""
    if STORIES_LOG_FILE.exists():
        with open(STORIES_LOG_FILE) as f:
            stories_data = json.load(f)
    else:
        stories_data = {"stories": [], "total_collected": 0, "session_start": datetime.datetime.utcnow().isoformat()}
    
    for story in stories:
        story["collected_at"] = datetime.datetime.utcnow().isoformat()
        stories_data["stories"].append(story)
    
    stories_data["total_collected"] = len(stories_data["stories"])
    
    with open(STORIES_LOG_FILE, "w") as f:
        json.dump(stories_data, f, indent=2)
    
    logger.info(f"💾 Logged {len(stories)} stories")

def log_fleet_event(event_type: str, data: dict):
    """Log to shared fleet coordination log"""
    if FLEET_LOG_FILE.exists():
        events = json.load(open(FLEET_LOG_FILE))
    else:
        events = {"events": []}
    
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event_type": event_type,
        "bot": "collector",
        "data": data
    }
    events["events"].append(event)
    
    with open(FLEET_LOG_FILE, "w") as f:
        json.dump(events, f, indent=2)

def log_earnings(job_hash, stories_collected, duration, estimated_mint):
    """Track earnings"""
    if EARNINGS_LOG_FILE.exists():
        earnings = json.load(open(EARNINGS_LOG_FILE))
    else:
        earnings = {
            "jobs": [],
            "total_mint_estimated": 0.0,
            "total_stories_collected": 0,
            "session_start": datetime.datetime.utcnow().isoformat()
        }
    
    earnings["jobs"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "job_hash": job_hash,
        "stories_collected": stories_collected,
        "duration_seconds": duration,
        "estimated_mint": estimated_mint
    })
    earnings["total_mint_estimated"] += estimated_mint
    earnings["total_stories_collected"] += stories_collected
    
    with open(EARNINGS_LOG_FILE, "w") as f:
        json.dump(earnings, f, indent=2)
    
    logger.info(f"💵 Session earnings: +{estimated_mint:.6f} MINT ({stories_collected} stories)")

def calculate_estimated_mint(complexity, duration_seconds, activity_ratio=1.0):
    """FoundryNet formula: 0.005 MINT/sec × complexity × activity_ratio^(-0.4) × decay"""
    base_rate = 0.005
    decay_multiplier = 0.98
    adjustment = activity_ratio ** (-0.4)
    total = base_rate * complexity * adjustment * decay_multiplier * duration_seconds
    return total

def print_session_summary():
    """Print earnings summary"""
    if EARNINGS_LOG_FILE.exists():
        earnings = json.load(open(EARNINGS_LOG_FILE))
        total = earnings["total_mint_estimated"]
        job_count = len(earnings["jobs"])
        total_stories = earnings["total_stories_collected"]
        avg_per_job = total / job_count if job_count > 0 else 0
        
        print("\n" + "="*80)
        print("🤖 CONTENT COLLECTOR BOT SESSION SUMMARY")
        print("="*80)
        print(f"   Total Collections Completed: {job_count}")
        print(f"   Total Stories Collected: {total_stories}")
        print(f"   Estimated MINT Earned: {total:.8f} MINT")
        print(f"   Average per Collection: {avg_per_job:.8f} MINT")
        print(f"   USD Value (@ $0.00005): ${total * 0.00005:.6f} USD")
        print(f"   Stories per Hour: {total_stories / (job_count * 2 / 60) if job_count > 0 else 0:.1f}")
        print("="*80 + "\n")

# -----------------------
# WORK SUBMISSION & COMPLETION
# -----------------------
def generate_job_hash(machine_uuid, work_type):
    """Generate unique job hash"""
    ts = int(time.time() * 1000)
    hash_input = f"{machine_uuid}|{work_type}|{ts}|{random.randint(0, 9999)}"
    hash_hex = hashlib.sha256(hash_input.encode()).hexdigest()
    return f"job_{hash_hex[:16]}_{ts}"

def submit_job(creds, job_hash, stories_collected: int):
    """Submit collection work"""
    payload = {
        "machine_uuid": creds["machine_uuid"],
        "job_hash": job_hash,
        "complexity": 1.5,  # Content collection is moderate complexity
        "payload": {
            "work_type": "Content Collection",
            "description": f"Collected {stories_collected} top stories from Hacker News",
            "source": "Hacker News",
            "stories_collected": stories_collected,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    }
    try:
        r = requests.post(f"{API_URL}/submit-job", json=payload, timeout=10)
        if r.ok:
            logger.info(f"✅ Job submitted: Content Collection ({stories_collected} stories)")
            return True
        else:
            logger.error(f"Job submission failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Submission failed: {e}")
        return False

def complete_job(creds, job_hash, work_duration: int):
    """Complete collection work"""
    try:
        signing_key = nacl.signing.SigningKey(base58.b58decode(creds["secret_key"]))
        timestamp = datetime.datetime.utcnow().isoformat()
        message = f"{job_hash}|{RECIPIENT_WALLET}|{timestamp}".encode()
        signature = signing_key.sign(message).signature
        signature_base58 = base58.b58encode(signature).decode()
        
        payload = {
            "machine_uuid": creds["machine_uuid"],
            "job_hash": job_hash,
            "recipient_wallet": RECIPIENT_WALLET,
            "completion_proof": {
                "timestamp": timestamp,
                "signature_base58": signature_base58
            }
        }
        
        r = requests.post(f"{API_URL}/complete-job", json=payload, timeout=10)
        if r.ok:
            result = r.json()
            logger.info(f"✅ Collection work completed | Tokens: {result.get('tokens_minted', 'pending')}")
            
            # Log earnings
            estimated_mint = calculate_estimated_mint(1.5, work_duration)
            
            # Count stories collected
            if STORIES_LOG_FILE.exists():
                stories_data = json.load(open(STORIES_LOG_FILE))
                session_start = stories_data.get("session_start", datetime.datetime.utcnow().isoformat())
                stories_this_session = len([
                    s for s in stories_data["stories"]
                    if s.get("collected_at", "") > session_start
                ])
            else:
                stories_this_session = 0
            
            log_earnings(job_hash, stories_this_session, work_duration, estimated_mint)
            return True
        else:
            logger.error(f"Job completion failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Completion failed: {e}")
        return False

# -----------------------
# MAIN LOOP
# -----------------------
def main():
    creds = load_or_create_machine()
    
    if not register_machine(creds):
        logger.error("Could not register with FoundryNet. Exiting.")
        return
    
    logger.info("🚀 Content Collector Bot starting...")
    logger.info(f"   Source: Hacker News")
    logger.info(f"   Work complexity: 1.5 (content collection)")
    logger.info(f"   Collection interval: 2 minutes")
    
    job_counter = 0
    
    try:
        while True:
            job_hash = generate_job_hash(creds["machine_uuid"], "content_collection")
            
            logger.info(f"\n[Collection #{job_counter + 1}] Starting HN collection...")
            collect_start = time.time()
            
            # Fetch stories
            stories = fetch_top_stories(limit=20)
            
            if not stories:
                logger.warning("Could not fetch stories, retrying in 120s...")
                time.sleep(120)
                continue
            
            # Log stories
            log_stories(stories)
            
            # Log fleet event
            log_fleet_event("stories_collected", {
                "count": len(stories),
                "top_story": stories[0]["title"] if stories else None,
                "total_score": sum(s["score"] for s in stories)
            })
            
            collect_duration = int(time.time() - collect_start)
            
            # Submit work
            if submit_job(creds, job_hash, len(stories)):
                logger.info(f"⏳ Collection took {collect_duration}s, waiting to complete...")
                time.sleep(60)  # Simulate processing time
                
                total_duration = collect_duration + 60
                complete_job(creds, job_hash, total_duration)
                
                logger.info("💤 Resting before next collection (120s)...")
                time.sleep(120)
            else:
                logger.warning("Job submission failed, retrying in 120s...")
                time.sleep(120)
            
            job_counter += 1
            
            # Print summary every 3 collections
            if job_counter % 3 == 0:
                print_session_summary()
    
    except KeyboardInterrupt:
        logger.info("🛑 Content Collector Bot shutting down...")
        print_session_summary()
        logger.info("👋 Goodbye!")

if __name__ == "__main__":
    main()
