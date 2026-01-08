"""
Document loading utilities for various file formats.
Supports markdown, JSON, text, and more.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a loaded document."""
    title: str
    source_path: str
    content: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate document fields."""
        if not self.title:
            self.title = Path(self.source_path).stem
        if not self.metadata:
            self.metadata = {}
        self.metadata.setdefault('load_time', datetime.utcnow().isoformat())
        self.metadata.setdefault('char_count', len(self.content))
        self.metadata.setdefault('word_count', len(self.content.split()))


class DocumentLoader:
    """Loads documents from various file formats."""
    
    SUPPORTED_EXTENSIONS = {'.md', '.txt', '.json'}
    
    @staticmethod
    async def load_file(file_path: Path) -> Optional[Document]:
        """Load a single file."""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if file_path.suffix not in DocumentLoader.SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file type: {file_path.suffix}")
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Parse based on extension
            if file_path.suffix == '.json':
                return DocumentLoader._parse_json(file_path, content)
            else:
                return DocumentLoader._parse_text(file_path, content)
                
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return None
    
    @staticmethod
    def _parse_text(file_path: Path, content: str) -> Document:
        """Parse text/markdown file."""
        # Extract title from first line if it's a markdown header
        lines = content.strip().split('\n')
        title = None
        
        if lines and lines[0].startswith('#'):
            title = lines[0].lstrip('#').strip()
            content = '\n'.join(lines[1:]).strip()
        
        return Document(
            title=title or file_path.stem,
            source_path=str(file_path),
            content=content,
            metadata={
                'file_type': file_path.suffix,
                'file_size': file_path.stat().st_size,
            }
        )
    
    @staticmethod
    def _parse_json(file_path: Path, content: str) -> Document:
        """Parse JSON file."""
        try:
            data = json.loads(content)
            
            # Handle different JSON structures
            if isinstance(data, dict):
                title = data.get('title', file_path.stem)
                text = data.get('content') or data.get('text') or json.dumps(data, indent=2)
                metadata = {k: v for k, v in data.items() if k not in ['title', 'content', 'text']}
            else:
                title = file_path.stem
                text = json.dumps(data, indent=2)
                metadata = {}
            
            metadata['file_type'] = '.json'
            metadata['file_size'] = file_path.stat().st_size
            
            return Document(
                title=title,
                source_path=str(file_path),
                content=text,
                metadata=metadata
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return DocumentLoader._parse_text(file_path, content)
    
    @staticmethod
    async def load_directory(
        directory: Path,
        recursive: bool = True,
        file_pattern: str = "*.*"
    ) -> List[Document]:
        """Load all supported files from a directory."""
        if not directory.exists():
            logger.error(f"Directory not found: {directory}")
            return []
        
        # Find all matching files
        if recursive:
            file_paths = list(directory.rglob(file_pattern))
        else:
            file_paths = list(directory.glob(file_pattern))
        
        # Filter by supported extensions
        file_paths = [
            fp for fp in file_paths
            if fp.is_file() and fp.suffix in DocumentLoader.SUPPORTED_EXTENSIONS
        ]
        
        logger.info(f"Found {len(file_paths)} files to load")
        
        # Load all files concurrently
        tasks = [DocumentLoader.load_file(fp) for fp in file_paths]
        documents = await asyncio.gather(*tasks)
        
        # Filter out None results
        documents = [doc for doc in documents if doc is not None]
        
        logger.info(f"Successfully loaded {len(documents)} documents")
        return documents
    
    @staticmethod
    async def load_from_paths(file_paths: List[Path]) -> List[Document]:
        """Load documents from a list of file paths."""
        tasks = [DocumentLoader.load_file(fp) for fp in file_paths]
        documents = await asyncio.gather(*tasks)
        documents = [doc for doc in documents if doc is not None]
        return documents
    
    @staticmethod
    def get_document_stats(documents: List[Document]) -> Dict[str, Any]:
        """Get statistics about loaded documents."""
        if not documents:
            return {
                'total_documents': 0,
                'total_chars': 0,
                'total_words': 0,
                'avg_doc_length': 0
            }
        
        total_chars = sum(len(doc.content) for doc in documents)
        total_words = sum(len(doc.content.split()) for doc in documents)
        
        return {
            'total_documents': len(documents),
            'total_chars': total_chars,
            'total_words': total_words,
            'avg_doc_length': total_chars // len(documents),
            'file_types': list(set(doc.metadata.get('file_type', 'unknown') for doc in documents))
        }


# Example usage
if __name__ == "__main__":
    async def test_loader():
        loader = DocumentLoader()
        
        # Load from directory
        docs = await loader.load_directory(Path("./big_tech_docs"))
        stats = loader.get_document_stats(docs)
        
        print(f"Loaded {stats['total_documents']} documents")
        print(f"Total words: {stats['total_words']:,}")
        print(f"File types: {stats['file_types']}")
        
        if docs:
            print(f"\nFirst document: {docs[0].title}")
            print(f"Content preview: {docs[0].content[:200]}...")
    
    asyncio.run(test_loader())
