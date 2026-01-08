"""
Semantic chunking with overlap and token-aware splitting.
Intelligently splits documents while preserving context.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk."""
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate chunk fields."""
        if not self.metadata:
            self.metadata = {}
        self.metadata['token_count'] = len(self.text.split())
        self.metadata['char_count'] = len(self.text)


class SemanticChunker:
    """
    Semantic chunking strategy that:
    1. Splits by paragraph boundaries
    2. Respects sentence boundaries
    3. Maintains target chunk size
    4. Adds overlap between chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        max_chunk_size: int = 1024
    ):
        """
        Args:
            chunk_size: Target chunk size in tokens (approximate)
            chunk_overlap: Number of tokens to overlap between chunks
            max_chunk_size: Maximum chunk size in tokens
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_size = max_chunk_size
        
        # Sentence boundary regex
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')
        # Paragraph boundary regex
        self.paragraph_pattern = re.compile(r'\n\s*\n')
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Chunk text using semantic boundaries.
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks
        
        Returns:
            List of Chunk objects
        """
        if not text.strip():
            logger.warning("Empty text provided for chunking")
            return []
        
        # First split by paragraphs
        paragraphs = self.paragraph_pattern.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_token_count = 0
        char_offset = 0
        
        for para in paragraphs:
            para_tokens = len(para.split())
            
            # If paragraph itself is too large, split by sentences
            if para_tokens > self.max_chunk_size:
                sentence_chunks = self._chunk_long_paragraph(para, metadata)
                chunks.extend(sentence_chunks)
                char_offset += len(para) + 2  # +2 for paragraph break
                continue
            
            # Check if adding this paragraph would exceed chunk size
            if current_token_count + para_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_index=len(chunks),
                    start_char=char_offset - len(chunk_text),
                    end_char=char_offset,
                    metadata=metadata.copy() if metadata else {}
                ))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk, self.chunk_overlap)
                current_chunk = [overlap_text, para] if overlap_text else [para]
                current_token_count = len(' '.join(current_chunk).split())
            else:
                # Add to current chunk
                current_chunk.append(para)
                current_token_count += para_tokens
            
            char_offset += len(para) + 2
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=char_offset - len(chunk_text),
                end_char=char_offset,
                metadata=metadata.copy() if metadata else {}
            ))
        
        logger.debug(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def _chunk_long_paragraph(
        self,
        paragraph: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split a long paragraph by sentences."""
        sentences = self.sentence_pattern.split(paragraph)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_token_count = 0
        
        for sentence in sentences:
            sentence_tokens = len(sentence.split())
            
            # If single sentence is too long, split by words
            if sentence_tokens > self.max_chunk_size:
                word_chunks = self._chunk_by_words(sentence, metadata)
                chunks.extend(word_chunks)
                continue
            
            if current_token_count + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_index=len(chunks),
                    start_char=0,  # Approximate
                    end_char=len(chunk_text),
                    metadata=metadata.copy() if metadata else {}
                ))
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap(current_chunk, self.chunk_overlap)
                current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                current_token_count = len(' '.join(current_chunk).split())
            else:
                current_chunk.append(sentence)
                current_token_count += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=0,
                end_char=len(chunk_text),
                metadata=metadata.copy() if metadata else {}
            ))
        
        return chunks
    
    def _chunk_by_words(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """Split text by words as last resort."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(Chunk(
                text=chunk_text,
                chunk_index=len(chunks),
                start_char=0,
                end_char=len(chunk_text),
                metadata=metadata.copy() if metadata else {}
            ))
        
        return chunks
    
    def _get_overlap(
        self,
        text_segments: List[str],
        overlap_tokens: int
    ) -> str:
        """Get overlap text from previous chunks."""
        # Combine all segments
        combined = ' '.join(text_segments)
        words = combined.split()
        
        # Take last N tokens
        if len(words) <= overlap_tokens:
            return combined
        
        overlap_words = words[-overlap_tokens:]
        return ' '.join(overlap_words)
    
    def chunk_documents(
        self,
        documents: List[Any],  # List of Document objects
        batch_size: int = 10
    ) -> Dict[Any, List[Chunk]]:
        """
        Chunk multiple documents.
        
        Returns:
            Dictionary mapping documents to their chunks
        """
        doc_chunks = {}
        
        for i, doc in enumerate(documents):
            try:
                # Add document metadata to chunks
                chunk_metadata = {
                    'document_id': i,
                    'document_title': doc.title,
                    'source_path': doc.source_path,
                    **doc.metadata
                }
                
                chunks = self.chunk_text(doc.content, chunk_metadata)
                doc_chunks[doc] = chunks
                
                logger.info(f"Chunked document '{doc.title}': {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error chunking document '{doc.title}': {e}")
                doc_chunks[doc] = []
        
        total_chunks = sum(len(chunks) for chunks in doc_chunks.values())
        logger.info(f"Total chunks created: {total_chunks}")
        
        return doc_chunks
    
    def get_chunk_stats(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Get statistics about chunks."""
        if not chunks:
            return {
                'total_chunks': 0,
                'avg_tokens': 0,
                'min_tokens': 0,
                'max_tokens': 0,
                'total_chars': 0
            }
        
        token_counts = [chunk.metadata['token_count'] for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_tokens': sum(token_counts) // len(chunks),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'total_chars': sum(len(chunk.text) for chunk in chunks)
        }


# Example usage
if __name__ == "__main__":
    chunker = SemanticChunker(chunk_size=512, chunk_overlap=50)
    
    sample_text = """
    # Introduction to AI
    
    Artificial Intelligence (AI) is revolutionizing technology. It encompasses machine learning, 
    deep learning, and natural language processing.
    
    ## Machine Learning
    
    Machine learning is a subset of AI that enables systems to learn from data. It uses 
    algorithms to identify patterns and make predictions without explicit programming.
    
    There are three main types: supervised learning, unsupervised learning, and reinforcement 
    learning. Each has its own use cases and applications.
    
    ## Deep Learning
    
    Deep learning uses neural networks with multiple layers. It has achieved remarkable success 
    in image recognition, speech synthesis, and game playing. Modern deep learning frameworks 
    include TensorFlow and PyTorch.
    """
    
    chunks = chunker.chunk_text(sample_text)
    stats = chunker.get_chunk_stats(chunks)
    
    print(f"Created {stats['total_chunks']} chunks")
    print(f"Average tokens per chunk: {stats['avg_tokens']}")
    print(f"\nFirst chunk:\n{chunks[0].text}")
