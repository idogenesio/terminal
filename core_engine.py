import yfinance as yf
import pandas_ta as ta
import pandas as pd
import numpy as np
import scipy.signal as signal
from dataclasses import dataclass
from typing import TypeAlias, Tuple

TickerStr: TypeAlias = str
Timestamp: TypeAlias = pd.Timestamp

@dataclass
class DivergenceSignal:
    type: str
    d1: Timestamp
    d2: Timestamp
    p1: float
    p2: float

class AnalyticsEngine:
    @staticmethod
    def fetch_data(ticker: TickerStr, period: str, interval: str) -> pd.DataFrame:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty: return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.atr(length=14, append=True)
        df.rename(columns={'RSI_14': 'RSI', 'ATRr_14': 'ATR'}, inplace=True)
        return df.dropna()

    @staticmethod
    def get_divergence(df: pd.DataFrame, order: int = 5) -> list[DivergenceSignal]:
        res = []
        prices = df['Close'].to_numpy()
        rsi = df['RSI'].to_numpy()
        
        # Bullish
        lows = signal.argrelextrema(prices, np.less, order=order)[0]
        for i in range(1, len(lows)):
            c, p = lows[i], lows[i-1]
            if prices[c] < prices[p] and rsi[c] > rsi[p]:
                res.append(DivergenceSignal('BULLISH', df.index[p], df.index[c], float(prices[p]), float(prices[c])))
        
        # Bearish
        highs = signal.argrelextrema(prices, np.greater, order=order)[0]
        for i in range(1, len(highs)):
            c, p = highs[i], highs[i-1]
            if prices[c] > prices[p] and rsi[c] < rsi[p]:
                res.append(DivergenceSignal('BEARISH', df.index[p], df.index[c], float(prices[p]), float(prices[c])))
        return res

    @staticmethod
    def get_zigzag(df: pd.DataFrame, threshold: float = None) -> Tuple[list, list]:
        """Improved structural pivot detection with dynamic volatility scaling."""
        prices = df['Close'].values.flatten()
        dates = df.index
        if len(prices) < 2: return [], []

        # Dynamic Threshold based on ATR if not provided
        if threshold is None:
            avg_price = df['Close'].mean()
            # Handle cases where ATR might be missing or all NaN
            if 'ATR' in df.columns and not df['ATR'].isnull().all():
                avg_atr = df['ATR'].mean()
                threshold = (avg_atr / avg_price) * 100 * 1.5 # 1.5x volatility factor
            else:
                threshold = 4.0 # Fallback to 4%
            threshold = max(2.5, min(threshold, 8.0)) # Clamp for stability
        
        px, py = [dates[0]], [prices[0]]
        last_pivot, trend = prices[0], 0
        
        for i in range(1, len(prices)):
            # Calculate percentage change from the last confirmed pivot
            diff = (prices[i] - last_pivot) / last_pivot * 100
            
            if trend == 0:
                if diff > threshold: trend = 1
                elif diff < -threshold: trend = -1
            
            if trend == 1:
                # If in uptrend, move the pivot up if price goes higher
                if prices[i] > last_pivot:
                    px[-1], py[-1], last_pivot = dates[i], prices[i], prices[i]
                # If price drops below threshold, confirm a new Down pivot
                elif diff < -threshold:
                    trend = -1
                    px.append(dates[i]); py.append(prices[i])
                    last_pivot = prices[i]
            
            elif trend == -1:
                # If in downtrend, move the pivot down if price goes lower
                if prices[i] < last_pivot:
                    px[-1], py[-1], last_pivot = dates[i], prices[i], prices[i]
                # If price rises above threshold, confirm a new Up pivot
                elif diff > threshold:
                    trend = 1
                    px.append(dates[i]); py.append(prices[i])
                    last_pivot = prices[i]
                    
        return px, py

    @staticmethod
    def run_monte_carlo(df: pd.DataFrame, days: int = 40, sims: int = 100) -> np.ndarray:
        """
        Geometric Brownian Motion (GBM) Engine:
        Uses log-normal returns with drift and volatility to model price paths.
        """
        # Convert to log returns for mathematical stability
        log_returns = np.log(1 + df['Close'].pct_change()).dropna()
        if log_returns.empty: return np.array([])
        
        u = log_returns.mean()
        var = log_returns.var()
        stdev = log_returns.std()
        
        # Calculate 'Drift' component: Expected return - 0.5 * variance
        drift = u - (0.5 * var)
        
        # Generate random 'Shocks' using normal distribution
        Z = np.random.normal(0, 1, (days, sims))
        
        # Path formula: S(t) = S(t-1) * exp(drift + stdev * shock)
        daily_returns = np.exp(drift + stdev * Z)
        
        paths = np.zeros((days, sims))
        paths[0] = df['Close'].iloc[-1]
        
        for t in range(1, days):
            paths[t] = paths[t-1] * daily_returns[t]
            
        return paths
