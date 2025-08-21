# Research Assistant

An AI-powered research assistant that transforms academic literature search through natural language interaction.

## Overview

Built as an MCP (Model Context Protocol) server for Claude Desktop, this tool provides intelligent access to multiple academic databases including PubMed, arXiv, and Semantic Scholar.

## Features

- **Multi-database search**: Query PubMed, arXiv, and Semantic Scholar simultaneously
- **Smart analysis**: Paper summarization, citation tracking, and trend identification  
- **Project management**: Organize papers by research topic with notes and tags
- **Export tools**: Generate bibliographies in multiple citation formats

## Quick Start

```bash
# Install dependencies
uv sync

# Run MCP server
uv run python src/main.py
```

## Status

**Early Development** - Core MCP server foundation complete, API integrations in progress.