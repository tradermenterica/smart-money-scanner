import pandas as pd
import io
import requests

class TickerSource:
    @staticmethod
    def get_darwinex_tickers():
        """
        Returns the list of tickers available in Darwinex as provided by the user.
        """
        raw_list = """
        AAL,CMCSA,GLW,LRCX
        AAPL,CME,GM,LUV
        ABBV,CMI,GOOG,LVS
        ABT,CNC,GOOGL,LYB
        ACN,COF,GS,MA
        ADBE,COP,GWW,MAR
        ADI,COST,HAL,MCD
        ADM,CRM,HCA,MCHP
        ADP,CSCO,HD,MCK
        ADSK,CSX,HLT,MDLZ
        AEP,CTSH,HON,MDT
        AIG,CVS,HPE,MET
        ALL,CVX,HPQ,META
        AMAT,D,HUM,MMM
        AMD,DAL,IBM,MO
        AMGN,DD,ICE,MPC
        AMT,DE,ILMN,MRK
        AMZN,DG,INTC,MS
        APD,DHI,INTU,MSFT
        AVGO,DHR,ISRG,MU
        AXP,DIS,ITW,NEE
        BA,DLTR,JCI,NEM
        BAC,DOW,JNJ,NFLX
        BAX,DUK,JPM,NKE
        BBY,EA,KDP,NOC
        BDX,EBAY,KEY,NSC
        BIIB,EL,KHC,NTAP
        BK,ELV,KLAC,NVDA
        BKNG,EMR,KMB,OKE
        BLK,EOG,KMI,OMC
        BMY,ETN,KO,ORCL
        BRKb,EW,KR,ORLY
        BSX,EXC,LEN,OXY
        C,EXPE,LLY,PANW
        CAH,FAST,LMT,PEP
        CAT,FDX,LOW,PFE
        CB,FIS,PG,PGR
        CCI,FITB,PH,PLD
        CCL,FOX,PM,PNC
        CHTR,FOXA,PPG,PRU
        CI,FTV,PSA,PYPL
        CLX,GD,QCOM,RCL
        CL,GE,REGN,RF
        CMA,GILD,ROK,ROST
        SBUX,SCHW,SHW,SLB
        SO,SPG,SPGI,SRE
        STT,STZ,SWK,SWKS
        SYF,SYK,SYY,T
        TGT,TJX,TMO,TMUS
        TRV,TSLA,TSN,TTWO
        TXN,UAL,ULTA,UNH
        UNP,UPS,USB,V
        VFC,VLO,VRTX,VZ
        WDAY,WDC,WFC,WM
        WMB,WMT,XOM,ZTS
        FISV,MRSH
        """
        # Clean and split the list
        tickers = []
        for line in raw_list.strip().split('\n'):
            parts = [t.strip().upper() for t in line.split(',') if t.strip()]
            tickers.extend(parts)
        
        return sorted(list(set(tickers)))

    @staticmethod
    def get_all_tickers():
        """
        Obtiene tickers desde una fuente confiable y masiva (NASDAQ, NYSE, AMEX).
        Aproximadamente 6000-8000 activos.
        """
        all_tickers = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # Fuente: rreichel3/US-Stock-Symbols (actualizado diariamente)
        sources = [
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.txt",
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nyse/nyse_tickers.txt",
            "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/amex/amex_tickers.txt"
        ]
        
        print("\n--- Descubrimiento Masivo de Tickers ---")
        
        for url in sources:
            try:
                exchange = url.split('/')[-2].upper()
                print(f"  Consultando {exchange}...")
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    # El formato es una lista de tickers, uno por línea
                    tickers = [t.strip().upper() for t in r.text.split('\n') if t.strip()]
                    all_tickers.extend(tickers)
                    print(f"    [OK] Agregados {len(tickers)} activos.")
                else:
                    print(f"    [FAIL] Error {r.status_code} en {exchange}")
            except Exception as e:
                print(f"    [ERROR] {url}: {e}")

        # Limpieza y filtrado básico para asegurar "Empresas Serias" (longitud de ticker estándar)
        unique = list(set([t for t in all_tickers if 1 <= len(t) <= 5]))
        
        print(f"--- Resultado: {len(unique)} tickers totales encontrados ---")
        
        if len(unique) < 1000:
             print("    [WARNING] Se encontraron pocos tickers, usando fallback...")
             return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
             
        return sorted(unique)
