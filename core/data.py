import yfinance as yf
import pandas as pd

class DataFetcher:
    @staticmethod
    def get_history(symbol: str, period="6mo", interval="1d") -> pd.DataFrame:
        """
        Descarga datos para un solo símbolo (Fallback).
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty: return pd.DataFrame()
            df.index = pd.to_datetime(df.index)
            return df
        except:
            return pd.DataFrame()

    @staticmethod
    def get_batch_history(symbols: list, period="3mo", interval="1d") -> pd.DataFrame:
        """
        Descarga datos para múltiples símbolos en una sola ráfaga (Batch).
        Esto es MUCHO más rápido que descargar uno por uno.
        """
        try:
            symbols_str = " ".join(symbols)
            # Descargamos todos a la vez
            df = yf.download(symbols_str, period=period, interval=interval, group_by='ticker', threads=True, progress=False)
            return df
        except Exception as e:
            print(f"[DATA] Error en descarga masiva: {e}")
            return pd.DataFrame()
