# main.py - Entry point
import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import twitter_config, openai_config
from bot import TwitterBot
from scheduler import BotScheduler

# Setup logging
def setup_logging():
    """Configure logging with file and console handlers."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

def check_credentials():
    """Verify all required credentials are set."""
    missing = []
    
    if not twitter_config.validate():
        missing.append("Twitter API credentials")
    
    if not openai_config.validate():
        missing.append("OpenAI API key")
    
    if missing:
        logger.error(f"Missing credentials: {', '.join(missing)}")
        logger.error("Please set environment variables in .env file")
        return False
    
    return True

def run_once(bot: TwitterBot):
    """Run bot once for testing."""
    logger.info("Running bot in single execution mode...")
    bot.run_daily_routine()
    
    stats = bot.get_stats()
    logger.info(f"Bot stats: {stats}")

def run_scheduled(bot: TwitterBot):
    """Run bot with scheduler."""
    logger.info("Starting bot in scheduled mode...")
    
    scheduler = BotScheduler(bot)
    scheduler.setup_default_schedule()
    
    logger.info("Bot is running. Press Ctrl+C to stop.")
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.id}: {job.next_run_time}")
    
    try:
        while True:
            time.sleep(60)
            # Log heartbeat
            stats = bot.get_stats()
            logger.debug(f"Heartbeat - Actions today: {stats['daily_actions']}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown signal received...")
        scheduler.shutdown()
        logger.info("Bot stopped")

def run_interactive(bot: TwitterBot):
    """Interactive mode for testing."""
    print("\\n" + "="*50)
    print("Twitter AI Bot - Interactive Mode")
    print("="*50 + "\\n")
    
    while True:
        print("\\nOptions:")
        print("1. Post morning tweet")
        print("2. Post main tweet")
        print("3. Post thread")
        print("4. Engage with timeline")
        print("5. Search and engage")
        print("6. Show stats")
        print("7. Run full routine")
        print("0. Exit")
        
        choice = input("\\nSelect option: ").strip()
        
        if choice == "1":
            bot.post_morning_tweet()
        elif choice == "2":
            bot.post_main_tweet()
        elif choice == "3":
            bot.post_thread()
        elif choice == "4":
            count = int(input("Max interactions (default 5): ") or "5")
            bot.engage_with_timeline(max_interactions=count)
        elif choice == "5":
            query = input("Search query (optional): ").strip() or None
            bot.search_and_engage(query=query)
        elif choice == "6":
            stats = bot.get_stats()
            print(f"\\nStats: {stats}")
        elif choice == "7":
            bot.run_daily_routine()
        elif choice == "0":
            break
        else:
            print("Invalid option")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Twitter AI Bot")
    parser.add_argument(
        "--mode", 
        choices=["once", "scheduled", "interactive"],
        default="scheduled",
        help="Run mode: once (single run), scheduled (daemon), interactive (manual)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - don't actually post to Twitter"
    )
    
    args = parser.parse_args()
    
    logger.info("="*50)
    logger.info("Twitter AI Bot Starting")
    logger.info(f"Mode: {args.mode}")
    logger.info("="*50)
    
    # Check credentials
    if not check_credentials():
        sys.exit(1)
    
    # Initialize bot
    try:
        bot = TwitterBot()
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        sys.exit(1)
    
    # Run based on mode
    if args.mode == "once":
        run_once(bot)
    elif args.mode == "scheduled":
        run_scheduled(bot)
    elif args.mode == "interactive":
        run_interactive(bot)

if __name__ == "__main__":
    main()
