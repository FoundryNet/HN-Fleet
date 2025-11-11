#!/usr/bin/env python3
"""
FoundryNet Content Processor Bot
Reads collector bot output, processes/tags stories, earns MINT for work
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
import re

# -----------------------
# SETUP
# -----------------------
API_URL = "https://lsijwmklicmqtuqxhgnu.supabase.co/functions/v1/main-ts"
CREDENTIALS_FILE = Path(os.path.expanduser("~/.foundry_processor_bot_credentials.json"))
PROCESSED_LOG_FILE = Path(os.path.expanduser("~/.foundry_processor_bot_processed.json"))
EARNINGS_LOG_FILE = Path(os.path.expanduser("~/.foundry_processor_bot_earnings.json"))
FLEET_LOG_FILE = Path(os.path.expanduser("~/.foundry_fleet_events.json"))
COLLECTOR_STORIES_FILE = Path(os.path.expanduser("~/.foundry_collector_bot_stories.json"))

RECIPIENT_WALLET = "3Cw2biz7aqpT9Zdz8tt2FZFUc7fFaYEqUc4kDsvjhg2b"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[FoundryNet %(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Content categories for tagging
CATEGORIES = {
    "AI": ["ai", "machine learning", "neural", "llm", "gpt", "claude", "model", "algorithm"],
    "Crypto": ["crypto", "bitcoin", "ethereum", "blockchain", "web3", "defi", "token"],
    "Startup": ["startup", "founder", "vc", "funding", "series", "launch", "company"],
    "Tech": ["technology", "api", "framework", "library", "open source", "github"],
    "Science": ["research", "paper", "study", "experiment", "physics", "biology"],
    "DevOps": ["deployment", "docker", "kubernetes", "devops", "infrastructure", "cloud"],
    "Security": ["security", "vulnerability", "exploit", "privacy", "encryption"],
    "Other": []
}

# -----------------------
# MACHINE ID
# -----------------------
def load_or_create_machine():
    """Load existing or create new machine credentials"""
    if CREDENTIALS_FILE.exists():
        creds = json.load(open(CREDENTIALS_FILE))
        logger.info(f"✅ Loaded existing processor bot identity: {creds['machine_uuid']}")
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
        logger.info(f"🆕 Generated new processor bot identity: {machine_uuid}")
        print(f"✅ Processor Bot Connected to FoundryNet.")
        print(f"Machine ID: {json.dumps(creds, indent=2)}")
        return creds

def register_machine(creds):
    """Register bot with FoundryNet"""
    payload = {
        "machine_uuid": creds["machine_uuid"],
        "machine_pubkey_base58": creds["public_key"],
        "metadata": {
            "os": "content_processor",
            "version": "1.0.0",
            "purpose": "content_categorization"
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
# CONTENT PROCESSING
# -----------------------
def read_collector_output():
    """Read stories from collector bot"""
    if not COLLECTOR_STORIES_FILE.exists():
        logger.warning("Collector bot stories not found yet")
        return []
    
    try:
        with open(COLLECTOR_STORIES_FILE) as f:
            data = json.load(f)
            stories = data.get("stories", [])
            logger.info(f"📖 Read {len(stories)} collected stories")
            return stories
    except Exception as e:
        logger.error(f"Failed to read collector output: {e}")
        return []

def categorize_story(story):
    """Categorize a story by title/url"""
    text = (story.get("title", "") + " " + story.get("url", "")).lower()
    
    detected_categories = []
    for category, keywords in CATEGORIES.items():
        if category == "Other":
            continue
        for keyword in keywords:
            if keyword in text:
                detected_categories.append(category)
                break
    
    return detected_categories if detected_categories else ["Other"]

def score_story(story):
    """Score story by engagement metrics"""
    score = story.get("score", 0)
    descendants = story.get("descendants", 0)
    
    # Simple engagement scoring
    engagement_score = (score * 0.7) + (descendants * 1.0)
    
    return engagement_score

def process_stories(stories):
    """Process and categorize stories"""
    processed = []
    
    for story in stories:
        categories = categorize_story(story)
        engagement = score_story(story)
        
        processed_story = {
            "id": story.get("id"),
            "title": story.get("title"),
            "url": story.get("url"),
            "categories": categories,
            "score": story.get("score", 0),
            "descendants": story.get("descendants", 0),
            "engagement_score": engagement,
            "collected_at": story.get("collected_at"),
            "processed_at": datetime.datetime.utcnow().isoformat()
        }
        
        processed.append(processed_story)
    
    # Sort by engagement
    processed.sort(key=lambda x: x["engagement_score"], reverse=True)
    
    logger.info(f"✅ Processed {len(processed)} stories")
    return processed

def log_processed(processed_stories):
    """Log processed stories"""
    if PROCESSED_LOG_FILE.exists():
        with open(PROCESSED_LOG_FILE) as f:
            data = json.load(f)
    else:
        data = {"processed": [], "total_processed": 0, "session_start": datetime.datetime.utcnow().isoformat()}
    
    data["processed"].extend(processed_stories)
    data["total_processed"] = len(data["processed"])
    
    with open(PROCESSED_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"💾 Logged {len(processed_stories)} processed stories")

def log_fleet_event(event_type: str, data: dict):
    """Log to shared fleet coordination log"""
    if FLEET_LOG_FILE.exists():
        events = json.load(open(FLEET_LOG_FILE))
    else:
        events = {"events": []}
    
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "event_type": event_type,
        "bot": "processor",
        "data": data
    }
    events["events"].append(event)
    
    with open(FLEET_LOG_FILE, "w") as f:
        json.dump(events, f, indent=2)

def log_earnings(job_hash, stories_processed, duration, estimated_mint):
    """Track earnings"""
    if EARNINGS_LOG_FILE.exists():
        earnings = json.load(open(EARNINGS_LOG_FILE))
    else:
        earnings = {
            "jobs": [],
            "total_mint_estimated": 0.0,
            "total_stories_processed": 0,
            "session_start": datetime.datetime.utcnow().isoformat()
        }
    
    earnings["jobs"].append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "job_hash": job_hash,
        "stories_processed": stories_processed,
        "duration_seconds": duration,
        "estimated_mint": estimated_mint
    })
    earnings["total_mint_estimated"] += estimated_mint
    earnings["total_stories_processed"] += stories_processed
    
    with open(EARNINGS_LOG_FILE, "w") as f:
        json.dump(earnings, f, indent=2)
    
    logger.info(f"💵 Session earnings: +{estimated_mint:.6f} MINT ({stories_processed} stories)")

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
        total_stories = earnings["total_stories_processed"]
        avg_per_job = total / job_count if job_count > 0 else 0
        
        print("\n" + "="*80)
        print("🤖 CONTENT PROCESSOR BOT SESSION SUMMARY")
        print("="*80)
        print(f"   Total Processing Runs: {job_count}")
        print(f"   Total Stories Processed: {total_stories}")
        print(f"   Estimated MINT Earned: {total:.8f} MINT")
        print(f"   Average per Run: {avg_per_job:.8f} MINT")
        print(f"   USD Value (@ $0.00005): ${total * 0.00005:.6f} USD")
        print(f"   Stories per Hour: {total_stories / (job_count * 3 / 60) if job_count > 0 else 0:.1f}")
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

def submit_job(creds, job_hash, stories_processed: int):
    """Submit processing work"""
    payload = {
        "machine_uuid": creds["machine_uuid"],
        "job_hash": job_hash,
        "complexity": 1.2,  # Content processing is moderate complexity
        "payload": {
            "work_type": "Content Processing",
            "description": f"Processed and categorized {stories_processed} stories",
            "stories_processed": stories_processed,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    }
    try:
        r = requests.post(f"{API_URL}/submit-job", json=payload, timeout=10)
        if r.ok:
            logger.info(f"✅ Job submitted: Content Processing ({stories_processed} stories)")
            return True
        else:
            logger.error(f"Job submission failed: {r.status_code}")
            return False
    except Exception as e:
        logger.error(f"Submission failed: {e}")
        return False

def complete_job(creds, job_hash, work_duration: int):
    """Complete processing work"""
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
            logger.info(f"✅ Processing work completed | Tokens: {result.get('tokens_minted', 'pending')}")
            
            # Log earnings
            estimated_mint = calculate_estimated_mint(1.2, work_duration)
            
            # Count stories processed
            if PROCESSED_LOG_FILE.exists():
                processed_data = json.load(open(PROCESSED_LOG_FILE))
                session_start = processed_data.get("session_start", datetime.datetime.utcnow().isoformat())
                stories_this_session = len([
                    s for s in processed_data["processed"]
                    if s.get("processed_at", "") > session_start
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
    
    logger.info("🚀 Content Processor Bot starting...")
    logger.info(f"   Categories: AI, Crypto, Startup, Tech, Science, DevOps, Security")
    logger.info(f"   Work complexity: 1.2 (content processing)")
    logger.info(f"   Processing interval: 3 minutes")
    
    job_counter = 0
    
    try:
        while True:
            job_hash = generate_job_hash(creds["machine_uuid"], "content_processing")
            
            logger.info(f"\n[Processing #{job_counter + 1}] Starting content processing...")
            process_start = time.time()
            
            # Read collector output
            stories = read_collector_output()
            
            if not stories:
                logger.warning("No stories to process yet, waiting...")
                time.sleep(180)
                continue
            
            # Process stories
            processed = process_stories(stories)
            
            if not processed:
                logger.warning("No stories processed, retrying...")
                time.sleep(180)
                continue
            
            # Log processed stories
            log_processed(processed)
            
            # Log fleet event with category breakdown
            categories_breakdown = {}
            for story in processed:
                for cat in story["categories"]:
                    categories_breakdown[cat] = categories_breakdown.get(cat, 0) + 1
            
            log_fleet_event("stories_processed", {
                "count": len(processed),
                "categories": categories_breakdown,
                "top_story": processed[0]["title"] if processed else None,
                "avg_engagement": sum(s["engagement_score"] for s in processed) / len(processed) if processed else 0
            })
            
            process_duration = int(time.time() - process_start)
            
            # Submit work
            if submit_job(creds, job_hash, len(processed)):
                logger.info(f"⏳ Processing took {process_duration}s, waiting to complete...")
                time.sleep(60)
                
                total_duration = process_duration + 60
                complete_job(creds, job_hash, total_duration)
                
                logger.info("💤 Resting before next processing (180s)...")
                time.sleep(180)
            else:
                logger.warning("Job submission failed, retrying...")
                time.sleep(180)
            
            job_counter += 1
            
            # Print summary every 3 runs
            if job_counter % 3 == 0:
                print_session_summary()
    
    except KeyboardInterrupt:
        logger.info("🛑 Content Processor Bot shutting down...")
        print_session_summary()
        logger.info("👋 Goodbye!")

if __name__ == "__main__":
    main()
