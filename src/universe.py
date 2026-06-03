"""IHSG tradable universe.

Phase 0-1 ships a curated list of the most liquid IDX names (LQ45 + popular
dividend stocks). The full IHSG has ~900 tickers; see load_full_universe() for
how to extend to the entire market via a CSV exported from IDX.
"""
from __future__ import annotations

import csv
import os

# Curated liquid universe (LQ45 core + common dividend/value names).
# Format: yfinance symbol (.JK suffix).
SEED_UNIVERSE: list[tuple[str, str, str]] = [
    # symbol, name, sector
    ("BBCA.JK", "Bank Central Asia", "Financials"),
    ("BBRI.JK", "Bank Rakyat Indonesia", "Financials"),
    ("BMRI.JK", "Bank Mandiri", "Financials"),
    ("BBNI.JK", "Bank Negara Indonesia", "Financials"),
    ("BRIS.JK", "Bank Syariah Indonesia", "Financials"),
    ("ARTO.JK", "Bank Jago", "Financials"),
    ("BBTN.JK", "Bank Tabungan Negara", "Financials"),
    ("BJBR.JK", "Bank BJB", "Financials"),
    ("TLKM.JK", "Telkom Indonesia", "Communication"),
    ("ISAT.JK", "Indosat", "Communication"),
    ("EXCL.JK", "XL Axiata", "Communication"),
    ("TOWR.JK", "Sarana Menara Nusantara", "Communication"),
    ("TBIG.JK", "Tower Bersama", "Communication"),
    ("ASII.JK", "Astra International", "Industrials"),
    ("UNTR.JK", "United Tractors", "Industrials"),
    ("PTBA.JK", "Bukit Asam", "Energy"),
    ("ITMG.JK", "Indo Tambangraya Megah", "Energy"),
    ("ADRO.JK", "Alamtri Resources (Adaro)", "Energy"),
    ("ADMR.JK", "Adaro Minerals", "Energy"),
    ("HRUM.JK", "Harum Energy", "Energy"),
    ("INDY.JK", "Indika Energy", "Energy"),
    ("MEDC.JK", "Medco Energi", "Energy"),
    ("PGAS.JK", "Perusahaan Gas Negara", "Energy"),
    ("AKRA.JK", "AKR Corporindo", "Energy"),
    ("ANTM.JK", "Aneka Tambang", "Basic Materials"),
    ("INCO.JK", "Vale Indonesia", "Basic Materials"),
    ("MDKA.JK", "Merdeka Copper Gold", "Basic Materials"),
    ("TINS.JK", "Timah", "Basic Materials"),
    ("INKP.JK", "Indah Kiat Pulp & Paper", "Basic Materials"),
    ("TKIM.JK", "Pabrik Kertas Tjiwi Kimia", "Basic Materials"),
    ("SMGR.JK", "Semen Indonesia", "Basic Materials"),
    ("INTP.JK", "Indocement", "Basic Materials"),
    ("BRPT.JK", "Barito Pacific", "Basic Materials"),
    ("TPIA.JK", "Chandra Asri", "Basic Materials"),
    ("UNVR.JK", "Unilever Indonesia", "Consumer Defensive"),
    ("ICBP.JK", "Indofood CBP", "Consumer Defensive"),
    ("INDF.JK", "Indofood Sukses Makmur", "Consumer Defensive"),
    ("MYOR.JK", "Mayora Indah", "Consumer Defensive"),
    ("HMSP.JK", "HM Sampoerna", "Consumer Defensive"),
    ("GGRM.JK", "Gudang Garam", "Consumer Defensive"),
    ("KLBF.JK", "Kalbe Farma", "Healthcare"),
    ("SIDO.JK", "Industri Jamu Sido Muncul", "Healthcare"),
    ("KAEF.JK", "Kimia Farma", "Healthcare"),
    ("CPIN.JK", "Charoen Pokphand Indonesia", "Consumer Defensive"),
    ("JPFA.JK", "Japfa Comfeed", "Consumer Defensive"),
    ("AMRT.JK", "Sumber Alfaria Trijaya", "Consumer Defensive"),
    ("MAPI.JK", "Mitra Adiperkasa", "Consumer Cyclical"),
    ("ACES.JK", "Aspirasi Hidup Indonesia (Ace)", "Consumer Cyclical"),
    ("ERAA.JK", "Erajaya Swasembada", "Consumer Cyclical"),
    ("MNCN.JK", "Media Nusantara Citra", "Communication"),
    ("SCMA.JK", "Surya Citra Media", "Communication"),
    ("JSMR.JK", "Jasa Marga", "Industrials"),
    ("WIKA.JK", "Wijaya Karya", "Industrials"),
    ("PTPP.JK", "PP (Persero)", "Industrials"),
    ("ADHI.JK", "Adhi Karya", "Industrials"),
    ("WSKT.JK", "Waskita Karya", "Industrials"),
    ("GOTO.JK", "GoTo Gojek Tokopedia", "Technology"),
    ("BUKA.JK", "Bukalapak", "Technology"),
    ("EMTK.JK", "Elang Mahkota Teknologi", "Technology"),
    ("BREN.JK", "Barito Renewables Energy", "Utilities"),
    ("POWR.JK", "Cikarang Listrindo", "Utilities"),
    ("CUAN.JK", "Petrindo Jaya Kreasi", "Energy"),
    ("PANI.JK", "Pantai Indah Kapuk Dua", "Real Estate"),
    ("BSDE.JK", "Bumi Serpong Damai", "Real Estate"),
    ("CTRA.JK", "Ciputra Development", "Real Estate"),
    ("SMRA.JK", "Summarecon Agung", "Real Estate"),
    ("PWON.JK", "Pakuwon Jati", "Real Estate"),
    ("AALI.JK", "Astra Agro Lestari", "Consumer Defensive"),
    ("LSIP.JK", "PP London Sumatra", "Consumer Defensive"),
    ("DSNG.JK", "Dharma Satya Nusantara", "Consumer Defensive"),
    ("MIKA.JK", "Mitra Keluarga Karyasehat", "Healthcare"),
    ("HEAL.JK", "Medikaloka Hermina", "Healthcare"),
    ("BNGA.JK", "Bank CIMB Niaga", "Financials"),
    ("PNLF.JK", "Panin Financial", "Financials"),
    ("BFIN.JK", "BFI Finance Indonesia", "Financials"),
]


def seed_universe() -> list[tuple[str, str, str]]:
    return list(SEED_UNIVERSE)


def load_full_universe(csv_path: str | None = None) -> list[tuple[str, str, str]]:
    """Load the full universe from a CSV (columns: symbol,name,sector).

    Export the list of listed companies from https://www.idx.co.id and save as
    data/universe.csv. Symbols may be bare codes (e.g. 'BBRI'); the '.JK' suffix
    is appended automatically for yfinance.
    """
    if csv_path is None:
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(here, "data", "universe.csv")
    if not os.path.exists(csv_path):
        return seed_universe()
    out: list[tuple[str, str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sym = (row.get("symbol") or "").strip().upper()
            if not sym:
                continue
            if not sym.endswith(".JK"):
                sym += ".JK"
            out.append((sym, (row.get("name") or "").strip(),
                        (row.get("sector") or "").strip()))
    return out or seed_universe()
