"""CEPEA commodity scraper via Playwright headless.

Scrapes prices from cepea.org.br bypassing Cloudflare protection.
Runs as a daily cron job — saves to PostgreSQL commodity_cache.

Usage:
    python -m src.scrapers.commodity_scraper          # scrape all
    python -m src.scrapers.commodity_scraper arroz     # scrape one
"""

import asyncio
import re
import sys
from datetime import date, datetime
from typing import Optional

from playwright.async_api import async_playwright

# CEPEA URLs for commodities without Yahoo Finance futures
CEPEA_URLS = {
    "arroz": "https://cepea.org.br/br/indicador/arroz.aspx",
    "feijao": "https://cepea.org.br/br/indicador/feijao.aspx",
}

CEPEA_UNITS = {
    "arroz": "saca (50kg)",
    "feijao": "saca (60kg)",
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _parse_soja_arroz_format(body_text: str) -> Optional[tuple[float, str]]:
    """Parse CEPEA format: date\\tprice\\tchange\\tchange\\tusd

    Example: 08/05/2026\\t127,70\\t0,25%\\t-0,92%\\t26,09
    """
    match = re.search(
        r"(\d{2}/\d{2}/\d{4})\t(\d{1,3}(?:\.\d{3})*,\d{2})\t",
        body_text,
    )
    if match:
        data_str = match.group(1)
        preco_str = match.group(2).replace(".", "").replace(",", ".")
        return float(preco_str), data_str
    return None


def _parse_feijao_format(body_text: str) -> Optional[tuple[float, str]]:
    """Parse feijão format: date\\tcity\\tprice\\tchange

    Example: 08-05-2026\\tCuritiba\\t388,21\\t-0,17%
    Takes first entry (Curitiba = CEPEA reference).
    """
    match = re.search(
        r"(\d{2}-\d{2}-\d{4})\t[\w\s./]+?\t(\d{1,3}(?:\.\d{3})*,\d{2})\t",
        body_text,
    )
    if match:
        data_str = match.group(1)
        preco_str = match.group(2).replace(".", "").replace(",", ".")
        # Convert dd-mm-yyyy to dd/mm/yyyy for consistency
        data_fmt = data_str.replace("-", "/")
        return float(preco_str), data_fmt
    return None


async def scrape_cepea(commodity: str) -> Optional[tuple[float, str]]:
    """Scrape price from CEPEA via Playwright headless (async).

    Returns (preco, data_referencia) or None if failed.
    """
    url = CEPEA_URLS.get(commodity)
    if not url:
        print(f"[SCRAPER] Commodity desconhecida: {commodity}", file=sys.stderr)
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=USER_AGENT)

            await page.goto(url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(3000)  # Wait for Cloudflare challenge

            title = await page.title()
            if "moment" in title.lower() or "cloudflare" in title.lower():
                print(f"[SCRAPER] Cloudflare bloqueou {commodity}", file=sys.stderr)
                await browser.close()
                return None

            body_text = await page.inner_text("body")
            await browser.close()

        # Parse based on commodity format
        if commodity == "feijao":
            result = _parse_feijao_format(body_text)
        else:
            result = _parse_soja_arroz_format(body_text)

        if result:
            preco, data_str = result
            print(f"[SCRAPER] {commodity}: R$ {preco:.2f} ({data_str})", file=sys.stderr)
            return preco, data_str

        print(f"[SCRAPER] {commodity}: preço não encontrado no HTML", file=sys.stderr)
        return None

    except Exception as e:
        print(f"[SCRAPER] Erro ao scrapar {commodity}: {e}", file=sys.stderr)
        return None


async def run_daily_scrape(commodity_filter: str = None) -> dict[str, bool]:
    """Scrape CEPEA prices and save to PostgreSQL.

    Args:
        commodity_filter: if set, scrape only this commodity.

    Returns:
        dict of {commodity: success_bool}
    """
    from src.services.database import set_commodity_cache

    results = {}
    commodities = [commodity_filter] if commodity_filter else list(CEPEA_URLS.keys())

    for commodity in commodities:
        if commodity not in CEPEA_URLS:
            results[commodity] = False
            continue

        result = await scrape_cepea(commodity)
        if result:
            preco, data_str = result
            try:
                # Parse date: dd/mm/yyyy
                parts = data_str.split("/")
                data_ref = date(int(parts[2]), int(parts[1]), int(parts[0]))

                await set_commodity_cache(
                    commodity=commodity,
                    preco=preco,
                    unidade=CEPEA_UNITS[commodity],
                    fonte="CEPEA/ESALQ",
                    data_referencia=data_ref,
                )
                results[commodity] = True
                print(f"[SCRAPER] {commodity} salvo: R$ {preco:.2f}", file=sys.stderr)
            except Exception as e:
                print(f"[SCRAPER] Erro ao salvar {commodity}: {e}", file=sys.stderr)
                results[commodity] = False
        else:
            results[commodity] = False

    return results


def main():
    """CLI entry point for cron job."""
    import asyncio

    commodity_filter = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"[SCRAPER] Iniciando scrape CEPEA (filter={commodity_filter})", file=sys.stderr)

    results = asyncio.run(run_daily_scrape(commodity_filter))

    for commodity, success in results.items():
        status = "OK" if success else "FALHOU"
        print(f"[SCRAPER] {commodity}: {status}", file=sys.stderr)

    if all(results.values()):
        print("[SCRAPER] Todos os scrapes concluídos com sucesso", file=sys.stderr)
        sys.exit(0)
    else:
        print("[SCRAPER] Alguns scrapes falharam", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
