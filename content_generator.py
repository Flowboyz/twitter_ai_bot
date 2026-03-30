# content_generator.py - LLM-based content generation
import openai
import logging
import random
import json
from typing import List, Optional, Dict
from datetime import datetime
from config import openai_config, bot_config

logger = logging.getLogger(__name__)

class ContentGenerator:
    """
    Generates Twitter content using OpenAI's API.
    Maintains consistent personality and avoids repetition.
    """
    
    def __init__(self, memory=None):
        self.memory = memory
        self.client = openai.OpenAI(api_key=openai_config.api_key)
        
        # Personality context for all generations
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with personality traits."""
        traits = ", ".join(bot_config.personality_traits)
        interests = ", ".join(bot_config.interests)
        
        return f"""You are {bot_config.bot_name}, a {bot_config.niche} enthusiast.
Personality: {traits}
Interests: {interests}
Writing style: {bot_config.writing_style}

Guidelines:
- Be authentic and human-like
- Share genuine insights, not generic advice
- Use casual language but demonstrate expertise
- Occasionally use humor or self-deprecation
- Avoid corporate speak and buzzwords
- Be concise but impactful
- Never use hashtags in the main content (they will be added separately)"""
    
    def _generate_text(self, prompt: str, max_tokens: int = None, temperature: float = None) -> str:
        """Generate text using OpenAI API with error handling."""
        try:
            response = self.client.chat.completions.create(
                model=openai_config.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens or openai_config.max_tokens,
                temperature=temperature or openai_config.temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return ""
    
    def generate_tweet(self, topic: Optional[str] = None, tone: Optional[str] = None) -> Dict[str, str]:
        """
        Generate an original tweet.
        
        Args:
            topic: Specific topic to tweet about (optional)
            tone: Specific tone (motivational, educational, humorous, etc.)
        
        Returns:
            Dict with 'content' and 'topics'
        """
        # Get recently used topics to avoid repetition
        recent_topics = []
        if self.memory:
            recent_topics = self.memory.get_recently_used_topics(hours=48)
        
        # Build prompt
        if topic:
            prompt = f"Write a tweet about {topic}."
        else:
            available_topics = [t for t in bot_config.interests if t not in recent_topics]
            if not available_topics:
                available_topics = bot_config.interests
            selected_topic = random.choice(available_topics)
            prompt = f"Write a tweet about {selected_topic}."
        
        if tone:
            prompt += f" Make it {tone}."
        
        prompt += " Keep it under 250 characters. No hashtags in the content."
        
        # Generate content
        content = self._generate_text(prompt, max_tokens=100)
        
        if not content:
            return None
        
        # Clean up content
        content = content.replace('"', '').strip()
        if len(content) > 280:
            content = content[:277] + "..."
        
        # Extract topics
        topics = self._extract_topics(content)
        
        return {
            'content': content,
            'topics': topics
        }
    
    def generate_thread(self, topic: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Generate a Twitter thread (series of connected tweets).
        
        Args:
            topic: Topic for the thread
        
        Returns:
            List of tweet dicts
        """
        if not topic:
            topic = random.choice(bot_config.interests)
        
        num_tweets = random.randint(*bot_config.thread_length_range)
        
        prompt = f"""Create a Twitter thread about {topic}.
Write {num_tweets} tweets that flow together naturally.
Make it educational but conversational.
Format as a JSON array where each item has 'content' field.
Keep each tweet under 270 characters.
No hashtags in the content."""
        
        try:
            response = self._generate_text(prompt, max_tokens=800, temperature=0.7)
            # Try to parse JSON
            if '[' in response and ']' in response:
                json_str = response[response.find('['):response.rfind(']')+1]
                tweets = json.loads(json_str)
            else:
                # Fallback: split by newlines
                tweets = [{'content': line.strip()} for line in response.split('\\n') if line.strip()]
            
            # Clean and validate
            cleaned_tweets = []
            for i, tweet in enumerate(tweets[:num_tweets]):
                content = tweet.get('content', '').replace('"', '').strip()
                if len(content) > 280:
                    content = content[:277] + "..."
                if content:
                    cleaned_tweets.append({
                        'content': content,
                        'topics': [topic] if i == 0 else []
                    })
            
            return cleaned_tweets
            
        except Exception as e:
            logger.error(f"Error generating thread: {e}")
            return []
    
    def generate_reply(self, tweet_text: str, author_username: str, 
                      context: Optional[str] = None) -> str:
        """
        Generate a contextual reply to a tweet.
        
        Args:
            tweet_text: The text of the tweet to reply to
            author_username: Username of the tweet author
            context: Additional context about the author or conversation
        
        Returns:
            Reply text
        """
        prompt = f"""Reply to this tweet by @{author_username}:
\"{tweet_text}\"

"""
        if context:
            prompt += f"Context: {context}\\n"
        
        prompt += """Guidelines:
- Be genuine and specific to their content
- Add value to the conversation
- Ask a question or share a relevant insight
- Keep it under 250 characters
- Don't be overly enthusiastic or use exclamation points excessively
- No hashtags"""
        
        reply = self._generate_text(prompt, max_tokens=100, temperature=0.8)
        
        if not reply:
            return ""
        
        # Clean up
        reply = reply.replace('"', '').strip()
        if len(reply) > 280:
            reply = reply[:277] + "..."
        
        return reply
    
    def generate_quote_tweet(self, tweet_text: str, author_username: str) -> str:
        """
        Generate a quote tweet with commentary.
        
        Args:
            tweet_text: Original tweet text
            author_username: Author's username
        
        Returns:
            Quote tweet text
        """
        prompt = f"""Write a quote tweet commenting on this by @{author_username}:
\"{tweet_text}\"

Add your perspective or insight. Keep it under 230 characters (to leave room for the quoted tweet).
Be thoughtful but casual. No hashtags."""
        
        quote = self._generate_text(prompt, max_tokens=100)
        
        if not quote:
            return ""
        
        quote = quote.replace('"', '').strip()
        if len(quote) > 280:
            quote = quote[:277] + "..."
        
        return quote
    
    def generate_hashtags(self, content: str, num_hashtags: int = 3) -> List[str]:
        """
        Generate relevant hashtags for a tweet.
        
        Args:
            content: Tweet content
            num_hashtags: Number of hashtags to generate
        
        Returns:
            List of hashtags
        """
        prompt = f"""Generate {num_hashtags} relevant hashtags for this tweet:
\"{content}\"

Use only these categories if relevant: AI, MachineLearning, Python, TechTwitter, BuildInPublic, DevCommunity, Coding, Developer, Startup, Tech, Programming.
Return only the hashtags separated by spaces, no explanation."""
        
        hashtags_text = self._generate_text(prompt, max_tokens=50, temperature=0.3)
        
        if not hashtags_text:
            return random.sample(bot_config.target_hashtags, min(num_hashtags, len(bot_config.target_hashtags)))
        
        # Parse hashtags
        hashtags = [tag.strip() for tag in hashtags_text.split() if tag.startswith('#')]
        
        # Ensure we have valid hashtags
        if len(hashtags) < num_hashtags:
            additional = random.sample(bot_config.target_hashtags, 
                                    num_hashtags - len(hashtags))
            hashtags.extend(additional)
        
        return hashtags[:num_hashtags]
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract main topics from content."""
        topics = []
        content_lower = content.lower()
        
        for interest in bot_config.interests:
            if interest.lower() in content_lower:
                topics.append(interest)
        
        return topics if topics else ["tech"]
    
    def generate_morning_tweet(self) -> Dict[str, str]:
        """Generate a morning motivational/insight tweet."""
        tones = ["motivational", "thought-provoking", "energetic"]
        tone = random.choice(tones)
        
        # Morning topics
        topics = ["productivity", "new beginnings", "learning", "goals"]
        topic = random.choice(topics)
        
        return self.generate_tweet(topic=topic, tone=tone)
    
    def generate_afternoon_tweet(self) -> Dict[str, str]:
        """Generate afternoon engagement tweet."""
        tones = ["conversational", "questioning", "observational"]
        tone = random.choice(tones)
        
        return self.generate_tweet(tone=tone)
    
    def generate_evening_tweet(self) -> Dict[str, str]:
        """Generate evening main content tweet."""
        # Higher chance of being educational or a hot take
        if random.random() < 0.3:
            return self.generate_tweet(tone="educational")
        else:
            return self.generate_tweet(tone="insightful")
