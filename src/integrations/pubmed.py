# ==============================================================================
# pubmed.py — PubMed E-utilities API Integration
# ==============================================================================
# Purpose: Connect to PubMed database for medical and biological literature search
# Sections: Imports, Constants, Client Class, Helper Functions
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library --------------------------------------------------------------
from typing import List, Dict, Any, Optional

# Third-Party -------------------------------------------------------------------
import httpx
from pydantic import BaseModel, Field

# Internal ----------------------------------------------------------------------
# TODO: Add internal imports when available
# from ..models.paper import Paper
# from ..utils.validation import validate_query

# ==============================================================================
# Public API
# ==============================================================================
__all__ = [
    "PubMedClient",
    "PubMedError",
    "PubMedPaper",
]

# ==============================================================================
# Configuration & Constants
# ==============================================================================

# PubMed API Settings
PUBMED_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_RATE_LIMIT = 3.0  # requests per second
MAX_RESULTS_LIMIT = 100
DEFAULT_TIMEOUT = 30

# API Endpoints
ESEARCH_ENDPOINT = "esearch.fcgi"
ESUMMARY_ENDPOINT = "esummary.fcgi"
EFETCH_ENDPOINT = "efetch.fcgi"

# ==============================================================================
# Data Models
# ==============================================================================

class PubMedPaper(BaseModel):
    """PubMed paper data model with validation."""
    
    id: str = Field(..., description="PubMed ID (PMID)")
    title: str = Field(..., min_length=1, description="Paper title")
    authors: List[Dict[str, str]] = Field(default_factory=list, description="Author information")
    journal: str = Field(default="", description="Journal name")
    publication_date: str = Field(default="", description="Publication date")
    doi: str = Field(default="", description="Digital Object Identifier")
    pmid: str = Field(..., description="PubMed ID")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    keywords: List[str] = Field(default_factory=list, description="Keywords/MeSH terms")

# ==============================================================================
# Exceptions
# ==============================================================================

class PubMedError(Exception):
    """Base exception for PubMed API errors."""
    pass

class PubMedRateLimitError(PubMedError):
    """Raised when API rate limit is exceeded."""
    pass

class PubMedAPIError(PubMedError):
    """Raised when API returns an error response."""
    pass

# ==============================================================================
# Main Implementation
# ==============================================================================

class PubMedClient:
    """PubMed E-utilities API client for academic literature search."""
    
    def __init__(
        self, 
        api_key: str, 
        email: str, 
        rate_limit: float = DEFAULT_RATE_LIMIT,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """Initialize PubMed client with API credentials.
        
        Args:
            api_key: PubMed API key for increased rate limits
            email: Required email address for API identification
            rate_limit: Requests per second (3.0 with key, 1.0 without)
            timeout: Request timeout in seconds
        """
        # FAIL FAST: Validate inputs immediately
        if not email or not email.strip():
            raise ValueError("Email address is required for PubMed API")
        
        if not "@" in email:
            raise ValueError(f"Invalid email format: {email}")
        
        if rate_limit <= 0 or rate_limit > 10:
            raise ValueError(f"Rate limit must be 0-10 requests/second, got: {rate_limit}")
        
        self.api_key = api_key.strip() if api_key else ""
        self.email = email.strip()
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.base_url = PUBMED_BASE_URL
    
    async def search_papers(
        self, 
        query: str, 
        max_results: int = 10,
        date_range: Optional[str] = None
    ) -> List[PubMedPaper]:
        """Search PubMed and return paper metadata.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-100)
            date_range: Optional date filter (e.g., "2023/01/01:2024/01/01")
            
        Returns:
            List of PubMedPaper objects
            
        Raises:
            ValueError: Invalid input parameters
            PubMedAPIError: API request failed
        """
        # FAIL FAST: Validate inputs immediately
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if not isinstance(max_results, int) or max_results < 1 or max_results > MAX_RESULTS_LIMIT:
            raise ValueError(f"max_results must be 1-{MAX_RESULTS_LIMIT}, got: {max_results}")
        
        query = query.strip()
        
        try:
            # 1️⃣ Search for PMIDs -----------------
            pmids = await self._search_pmids(query, max_results, date_range)
            
            if not pmids:
                return []
            
            # 2️⃣ Fetch paper details -----------------
            return await self._fetch_paper_details(pmids)
            
        except httpx.HTTPError as e:
            raise PubMedAPIError(f"PubMed API request failed: {e}")
        except Exception as e:
            raise PubMedError(f"Unexpected error during PubMed search: {e}")
    
    async def _search_pmids(
        self, 
        query: str, 
        max_results: int,
        date_range: Optional[str] = None
    ) -> List[str]:
        """Search PubMed for PMIDs matching query."""
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "tool": "research_assistant",
            "email": self.email,
        }
        
        # Add API key if available
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        # Add date range filter if specified
        if date_range:
            search_params["datetype"] = "pdat"
            search_params["mindate"] = date_range.split(":")[0] if ":" in date_range else date_range
            if ":" in date_range:
                search_params["maxdate"] = date_range.split(":")[1]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}{ESEARCH_ENDPOINT}", params=search_params)
            response.raise_for_status()
            
            search_data = response.json()
            
            # Check for API errors
            if "error" in search_data:
                raise PubMedAPIError(f"PubMed search error: {search_data['error']}")
            
            return search_data.get("esearchresult", {}).get("idlist", [])
    
    async def _fetch_paper_details(self, pmids: List[str]) -> List[PubMedPaper]:
        """Fetch detailed paper information for given PMIDs."""
        if not pmids:
            return []
        
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "tool": "research_assistant",
            "email": self.email,
        }
        
        # Add API key if available
        if self.api_key:
            fetch_params["api_key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}{ESUMMARY_ENDPOINT}", params=fetch_params)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if "error" in data:
                raise PubMedAPIError(f"PubMed fetch error: {data['error']}")
            
            papers = []
            result_data = data.get("result", {})
            
            for pmid in pmids:
                paper_data = result_data.get(pmid)
                if not paper_data or pmid == "uids":
                    continue
                
                try:
                    # Extract and clean paper data
                    paper = PubMedPaper(
                        id=pmid,
                        title=self._clean_title(paper_data.get("title", "")),
                        authors=self._extract_authors(paper_data.get("authors", [])),
                        journal=paper_data.get("source", ""),
                        publication_date=paper_data.get("pubdate", ""),
                        doi=self._extract_doi(paper_data.get("elocationid", "")),
                        pmid=pmid,
                        abstract=None,  # Summary endpoint doesn't include abstracts
                        keywords=[]     # Would need separate MeSH terms fetch
                    )
                    papers.append(paper)
                    
                except Exception as e:
                    print(f"Warning: Failed to parse paper {pmid}: {e}")
                    continue
            
            return papers

# ==============================================================================
# Helper Functions
# ==============================================================================

    def _clean_title(self, title: str) -> str:
        """Clean and format paper title."""
        if not title:
            return "No title available"
        
        # Remove HTML tags and extra whitespace
        import re
        title = re.sub(r"<[^>]+>", "", title)
        title = re.sub(r"\s+", " ", title).strip()
        
        return title
    
    def _extract_authors(self, authors_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract and format author information."""
        authors = []
        
        for author in authors_data:
            if isinstance(author, dict):
                name = author.get("name", "")
                if name:
                    # Split name into components if possible
                    name_parts = name.split()
                    if len(name_parts) >= 2:
                        authors.append({
                            "name": name,
                            "lastname": name_parts[-1],
                            "forename": " ".join(name_parts[:-1])
                        })
                    else:
                        authors.append({"name": name})
        
        return authors
    
    def _extract_doi(self, elocation_id: str) -> str:
        """Extract DOI from elocation ID."""
        if not elocation_id:
            return ""
        
        # Remove "doi: " prefix if present
        doi = elocation_id.replace("doi: ", "").strip()
        
        # Validate DOI format (basic check)
        if doi and "/" in doi:
            return doi
        
        return ""