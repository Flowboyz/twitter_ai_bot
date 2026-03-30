# config.py - Configuration management
import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TwitterConfig:
    """Twitter API configuration."""
    bearer_token: str = os.getenv("TWITTER_BEARER_TOKEN", "")
    api_key: str = os.getenv("TWITTER_API_KEY", "")
    api_secret: str = os.getenv("TWITTER_API_SECRET", "")
    access_token: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    access_token_secret: str = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
    
    # Rate limiting settings (to avoid bans)
    max_tweets_per_hour: int = 5
    max_replies_per_hour: int = 10
    max_retweets_per_hour: int = 5
    max_likes_per_hour: int = 15
    
    # Delays (in seconds)
    min_delay_between_actions: int = 30
    max_delay_between_actions: int = 180
    min_delay_between_tweets: int = 3600  # 1 hour
    
    def validate(self) -> bool:
        """Validate that all required credentials are present."""
        return all([
            self.bearer_token,
            self.api_key,
            self.api_secret,
            self.access_token,
            self.access_token_secret
        ])

@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    temperature: float = 0.8
    max_tokens: int = 150
    
    def validate(self) -> bool:
        """Validate OpenAI configuration."""
        return bool(self.api_key)

@dataclass
class BotConfig:
    """Bot behavior configuration."""
    # Bot identity
    bot_name: str = "TechAI_Insider"
    niche: str = "Tech and AI"
    
    # Personality traits (influence content generation)
    personality_traits: List[str] = None
    interests: List[str] = None
    writing_style: str = "smart but casual, occasionally humorous"
    
    # Content generation settings
    tweet_length_range: tuple = (100, 250)
    thread_length_range: tuple = (3, 7)
    
    # Scheduling
    timezone: str = "UTC"
    
    # Search queries for finding content to engage with
    search_queries: List[str] = None
    
    # Target hashtags for engagement
    target_hashtags: List[str] = None
    
    def __post_init__(self):
        if self.personality_traits is None:
            self.personality_traits = [
                "curious about emerging tech",
                "pragmatic about AI limitations",
                "enthusiastic about developer tools",
                "skeptical of hype cycles",
                "helpful and educational"
            ]
        
        if self.interests is None:
            self.interests = [
                "machine learning",
                "Python programming",
                "AI ethics",
                "startup culture",
                "developer productivity",
                "open source",
                "future of work"
            ]
        
        if self.search_queries is None:
            self.search_queries = [
                "artificial intelligence",
                "machine learning",
                "Python programming",
                "AI tools",
                "developer tips",
                "startup advice",
                "tech trends"
            ]
        
        if self.target_hashtags is None:
            self.target_hashtags = [
                "#AI", "#MachineLearning", "#Python", "#TechTwitter",
                "#BuildInPublic", "#DevCommunity", "#ArtificialIntelligence",
                "#Coding", "#Developer", "#Startup"
            ]

# Global configuration instances
twitter_config = TwitterConfig()
openai_config = OpenAIConfig()
bot_config = BotConfig()


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    enabled: bool = os.getenv("DASHBOARD_ENABLED", "true").lower() == "true"
    host: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port: int = int(os.getenv("DASHBOARD_PORT", "5000"))

@dataclass
class WebhookConfig:
    """Webhook configuration."""
    discord_url: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    slack_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    custom_urls: List[str] = None
    
    def __post_init__(self):
        if self.custom_urls is None:
            custom = os.getenv("CUSTOM_WEBHOOK_URLS", "")
            self.custom_urls = [u.strip() for u in custom.split(",") if u.strip()]

@dataclass
class ImageConfig:
    """DALL-E image generation config."""
    enabled: bool = os.getenv("IMAGE_GENERATION_ENABLED", "true").lower() == "true"
    max_daily: int = int(os.getenv("MAX_DAILY_IMAGES", "10"))
    model: str = os.getenv("DALLE_MODEL", "dall-e-3")

# Update instances
dashboard_config = DashboardConfig()
webhook_config = WebhookConfig()
image_config = ImageConfig()
