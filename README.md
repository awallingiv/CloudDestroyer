# CloudDestroyer

A powerful Cloudflare bypass scraper designed to defeat protection mechanisms and access protected content.

## Features

- **Multi-Strategy Bypass**: Combines cloudscraper, Selenium stealth, and Playwright for maximum success
- **Challenge Detection**: Automatically identifies protection types and selects optimal bypass method
- **Fingerprint Spoofing**: Advanced browser fingerprinting and stealth capabilities
- **Session Management**: Persistent bypass tokens and cookie handling
- **Retry Logic**: Intelligent fallback and retry mechanisms

## Quick Start

```python
from src.core.cloud_destroyer import CloudDestroyer

# Initialize the scraper
scraper = CloudDestroyer()

# Bypass Cloudflare and get content
response = scraper.get("https://protected-site.com")
print(response.text)
```

## Installation

```bash
pip install -r requirements.txt
```

## Legal Notice

This tool is for educational and legitimate research purposes only. Users are responsible for compliance with applicable laws and website terms of service.