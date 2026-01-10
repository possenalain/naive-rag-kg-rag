import asyncio
from src.utils.graph import get_graph
from graphiti_core.nodes import EpisodeType
from datetime import datetime

async def test():
    g = await get_graph()
    print(f"Testing Graphiti with model: gemini-1.5-flash-002")
    
    try:
        episode = await g.graphiti.add_episode(
            name='Test Episode',
            episode_body='OpenAI raised $6.6 billion in funding from Microsoft, NVIDIA, and other investors.',
            source=EpisodeType.text,
            source_description='Test episode for Gemini 2.0 Flash',
            reference_time=datetime.now()
        )
        print(f'✓ Success! Episode created: {episode.name}')
        print(f'  Episode UUID: {episode.uuid}')
        return True
    except Exception as e:
        print(f'✗ Error: {e}')
        return False

if __name__ == '__main__':
    success = asyncio.run(test())
    exit(0 if success else 1)
