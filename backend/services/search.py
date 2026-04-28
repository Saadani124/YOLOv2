"""
Enhanced Search Service for ScanVD
Advanced search with fuzzy matching, ranking, and stemming
"""
from typing import List, Dict, Tuple
from difflib import SequenceMatcher
from collections import Counter
import re

from config import (
    SEARCH_FUZZY_THRESHOLD, SEARCH_MAX_RESULTS,
    SEARCH_ENABLE_STEMMING
)

# Simple stemming cache
_stem_cache = {}


def simple_stem(word: str) -> str:
    """
    Simple word stemming (removes common suffixes).
    
    Args:
        word: Word to stem
        
    Returns:
        Stemmed word
    """
    if word in _stem_cache:
        return _stem_cache[word]
    
    word = word.lower()
    
    # Remove common suffixes
    suffixes = ['ing', 'ed', 'es', 's', 'ly', 'er', 'est', 'tion', 'ness']
    for suffix in suffixes:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            stemmed = word[:-len(suffix)]
            _stem_cache[word] = stemmed
            return stemmed
    
    _stem_cache[word] = word
    return word


def fuzzy_match(s1: str, s2: str) -> float:
    """
    Calculate fuzzy match score between two strings.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def calculate_tf_idf_scores(segments: List[Dict], query_words: List[str]) -> Dict[int, float]:
    """
    Calculate TF-IDF scores for segments based on query words.
    
    Args:
        segments: List of segment dictionaries
        query_words: List of query words
        
    Returns:
        Dictionary mapping segment index to TF-IDF score
    """
    # Document frequency (how many segments contain each word)
    df = Counter()
    segment_words = []
    
    for seg in segments:
        words = set(simple_stem(w) for w in seg["text"].lower().split())
        segment_words.append(words)
        for word in words:
            df[word] += 1
    
    # Calculate scores
    scores = {}
    num_segments = len(segments)
    
    for idx, words in enumerate(segment_words):
        score = 0.0
        for query_word in query_words:
            stemmed_query = simple_stem(query_word)
            
            # Term frequency in this segment
            if stemmed_query in words:
                tf = 1.0  # Binary: word present or not
                # Inverse document frequency
                idf = num_segments / (df[stemmed_query] + 1)
                score += tf * idf
        
        scores[idx] = score
    
    return scores


def search_transcription(
    segments: List[Dict],
    query: str,
    full_text: str = ""
) -> List[Dict]:
    """
    Enhanced search with fuzzy matching, ranking, and stemming.
    
    Args:
        segments: List of segment dictionaries with text and timestamps
        query: Search query string
        full_text: Optional full transcription text
        
    Returns:
        Ranked list of matching segments with scores
    """
    # Clean up query: remove extra spaces and punctuation for matching
    query_clean = re.sub(r'[^\w\s]', '', query).lower().strip()
    query_lower = query.lower().strip()
    query_words = query_lower.split()
    
    # Stem query words if enabled
    if SEARCH_ENABLE_STEMMING:
        stemmed_query_words = [simple_stem(w) for w in query_words]
    else:
        stemmed_query_words = query_words
    
    results = []
    
    # Calculate TF-IDF scores for ranking
    tfidf_scores = calculate_tf_idf_scores(segments, query_words)
    
    # Search through segments
    for idx, segment in enumerate(segments):
        segment_text = segment["text"]
        segment_text_lower = segment_text.lower()
        
        # 0. Precise phrase match (highest priority - including punctuation)
        if query_lower in segment_text_lower:
            match = _create_match(
                segment=segment,
                match_type="exact",
                score=100.0 + tfidf_scores.get(idx, 0.0),
                query=query,
            )
            results.append(match)
            continue
            
        # 1. Cleaned phrase match (remove punctuation from both)
        segment_text_clean = re.sub(r'[^\w\s]', '', segment_text_lower)
        if query_clean in segment_text_clean:
            match = _create_match(
                segment=segment,
                match_type="phrase",
                score=95.0 + tfidf_scores.get(idx, 0.0),
                query=query,
            )
            results.append(match)
            continue
        
        # 2. All words present (high priority)
        segment_words = set(segment_text_lower.split())
        if SEARCH_ENABLE_STEMMING:
            segment_stems = set(simple_stem(w) for w in segment_words)
            query_stems_set = set(stemmed_query_words)
            if query_stems_set.issubset(segment_stems):
                match = _create_match(
                    segment=segment,
                    match_type="all_words",
                    score=80.0 + tfidf_scores.get(idx, 0.0),
                    query=query,
                    matched_words=query_words,
                )
                results.append(match)
                continue
        else:
            if all(word in segment_text_lower for word in query_words):
                match = _create_match(
                    segment=segment,
                    match_type="all_words",
                    score=80.0 + tfidf_scores.get(idx, 0.0),
                    query=query,
                    matched_words=query_words,
                )
                results.append(match)
                continue
        
        # 3. Fuzzy match (medium priority)
        fuzzy_score = fuzzy_match(query_lower, segment_text_lower)
        if fuzzy_score >= SEARCH_FUZZY_THRESHOLD:
            match = _create_match(
                segment=segment,
                match_type="fuzzy",
                score=fuzzy_score * 60.0 + tfidf_scores.get(idx, 0.0),
                query=query,
            )
            results.append(match)
            continue
        
        # 4. Partial word match (lower priority)
        if SEARCH_ENABLE_STEMMING:
            matching_stems = [w for w in stemmed_query_words if w in segment_stems]
            match_ratio = len(matching_stems) / len(stemmed_query_words)
        else:
            matching_words = [w for w in query_words if w in segment_text_lower]
            match_ratio = len(matching_words) / len(query_words)
        
        # Require at least 50% of words to match
        if match_ratio >= 0.5:
            match = _create_match(
                segment=segment,
                match_type="partial",
                score=match_ratio * 40.0 + tfidf_scores.get(idx, 0.0),
                query=query,
                matched_words=matching_words if not SEARCH_ENABLE_STEMMING else None,
            )
            results.append(match)
    
    # Sort by score (descending)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # Limit results
    results = results[:SEARCH_MAX_RESULTS]
    
    # Enhance with word-level timestamps if available
    for result in results:
        _add_word_level_timestamp(result, query_lower)
    
    return results


def _create_match(
    segment: Dict,
    match_type: str,
    score: float,
    query: str,
    matched_words: List[str] = None
) -> Dict:
    """
    Create a search match result.
    
    Args:
        segment: Segment dictionary
        match_type: Type of match (exact, fuzzy, partial, etc.)
        score: Match score
        query: Original query
        matched_words: List of matched words (optional)
        
    Returns:
        Match result dictionary
    """
    match = {
        "segment_id": segment["id"],
        "start": segment["start"],
        "end": segment["end"],
        "start_formatted": segment["start_formatted"],
        "end_formatted": segment["end_formatted"],
        "text": segment["text"],
        "match_type": match_type,
        "score": round(score, 2),
    }
    
    if matched_words:
        match["matched_words"] = matched_words
    
    return match


def _add_word_level_timestamp(match: Dict, query: str):
    """
    Add precise word-level timestamp to match if available.
    
    Args:
        match: Match dictionary to enhance
        query: Search query
    """
    if "words" not in match or not match.get("words"):
        return
    
    query_words = query.lower().split()
    query_clean = re.sub(r'[^\w\s]', '', query.lower())
    words = match["words"]
    
    # Try exact match sequence of words
    for i in range(len(words)):
        # Check window of words matching query length
        for length in range(len(query_words), len(query_words) + 3):
            if i + length > len(words):
                break
                
            window_words = words[i:i + length]
            window_text = " ".join(w["word"].lower() for w in window_words)
            window_clean = re.sub(r'[^\w\s]', '', window_text)
            
            if query_clean in window_clean:
                match["precise_start"] = words[i]["start"]
                match["precise_start_formatted"] = words[i]["start_formatted"]
                return


def highlight_matches(text: str, query: str) -> str:
    """
    Add HTML highlighting to matched text.
    
    Args:
        text: Original text
        query: Search query
        
    Returns:
        Text with <mark> tags around matches
    """
    query_words = query.lower().split()
    
    # Escape special regex characters
    def escape_regex(s):
        return re.escape(s)
    
    # Highlight each query word
    highlighted = text
    for word in query_words:
        pattern = re.compile(f'({escape_regex(word)})', re.IGNORECASE)
        highlighted = pattern.sub(r'<mark>\1</mark>', highlighted)
    
    return highlighted


def get_search_suggestions(segments: List[Dict], query: str, limit: int = 5) -> List[str]:
    """
    Get search suggestions based on partial query.
    
    Args:
        segments: List of segments
        query: Partial search query
        limit: Maximum number of suggestions
        
    Returns:
        List of suggested queries
    """
    query_lower = query.lower().strip()
    
    if len(query_lower) < 2:
        return []
    
    # Extract all unique phrases (2-4 words)
    phrases = set()
    for seg in segments:
        words = seg["text"].lower().split()
        for i in range(len(words)):
            for length in range(2, 5):  # 2-4 word phrases
                if i + length <= len(words):
                    phrase = " ".join(words[i:i+length])
                    if query_lower in phrase:
                        phrases.add(phrase)
    
    # Sort by relevance (starts with query first)
    suggestions = sorted(
        phrases,
        key=lambda p: (not p.startswith(query_lower), len(p))
    )
    
    return suggestions[:limit]

def count_results(segments: List[Dict], query: str) -> int:
    """
    Count the number of segments that match the search query.
    
    Args:
        segments: List of segment dictionaries
        query: Search query string
        
    Returns:
        Number of matching results
    """
    results = search_transcription(segments, query)
    return len(results)