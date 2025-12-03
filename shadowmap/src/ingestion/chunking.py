from typing import List
import re

class SemanticChunker:
    """
    Splits text into semantic chunks suitable for embedding and LLM processing.
    Simple implementation for Phase 1: Split by paragraphs/newlines with overlap.
    """
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """
        Split text into chunks.
        """
        if not text:
            return []
            
        # Normalize newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            if current_length + para_len > self.chunk_size and current_chunk:
                # Join current chunk and add to list
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)
                
                # Handle overlap - keep last paragraph if it fits
                # For simplicity in Phase 1, we just start fresh or keep last if small
                if len(current_chunk[-1]) < self.overlap:
                     current_chunk = [current_chunk[-1]]
                     current_length = len(current_chunk[-1])
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(para)
            current_length += para_len
            
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
