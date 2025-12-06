from typing import List
import re

class SemanticChunker:
    """
    Splits text into semantic chunks suitable for embedding and LLM processing.
    Simple implementation for Phase 1: Split by paragraphs/newlines with overlap.
    """
    
    def __init__(self, chunk_size: int = 500000, overlap: int = 2000):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """
        Split text into chunks.
        Uses a hybrid approach: split by paragraphs first, but enforce a hard limit 
        to ensure no chunk is too large (forcing better LLM attention).
        """
        if not text:
            return []
            
        # 1. First, split by something reasonable (newlines)
        # We replace multiple newlines with a unique delimiter to split safely
        text = re.sub(r'\n+', '\n', text) # Normalize to single newlines
        paragraphs = text.split('\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        target_size = self.chunk_size # e.g., 2000 chars
        
        for para in paragraphs:
            # If a single paragraph is HUGE (rare but possible in bad HTML), split it hard
            if len(para) > target_size:
                # Flush current if any
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split the long paragraph into fixed sizes
                for i in range(0, len(para), target_size - self.overlap):
                    chunks.append(para[i : i + target_size])
                continue

            # Normal accumulation
            if current_length + len(para) > target_size and current_chunk:
                # Close the chunk
                chunks.append("\n".join(current_chunk))
                
                # Overlap: keep the last paragraph(s) to maintain context
                # Simple overlapping: keep last paragraph
                overlap_text = current_chunk[-1]
                current_chunk = [overlap_text]
                current_length = len(overlap_text)
            
            current_chunk.append(para)
            current_length += len(para)
            
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks
