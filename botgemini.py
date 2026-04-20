import matplotlib.pyplot as plt
from matplotlib.widgets import TextBox, Button
import numpy as np
import pandas as pd
import os
from datetime import datetime
from core_engine import AnalyticsEngine, TickerStr

# ==========================================
# PROFESSIONAL TERMINAL PALETTE
# ==========================================
C_BG = '#080808'       # Deep Black
C_GRID = '#1e1e1e'     # Very Subtle Grid
C_UP = '#00ff66'       # Success Green
C_DOWN = '#ff3366'     # Danger Red
C_PRICE = '#ffffff'    # Clean White
C_NEON_BLUE = '#00d4ff'
C_NEON_PURPLE = '#bd93f9'

class BotGeminiTerminal:
    def __init__(self) -> None:
        self.ticker: TickerStr = "TOWR.JK"
        self.interval, self.period = "1wk", "2y"
        self.mode = "STANDARD"
        self.save_dir = "captures"
        if not os.path.exists(self.save_dir): os.makedirs(self.save_dir)
        
        # Professional High-DPI Figure
        self.fig = plt.figure(figsize=(16, 9), facecolor=C_BG, dpi=100)
        gs = self.fig.add_gridspec(4, 1, height_ratios=[4, 1, 1, 1], hspace=0.1)
        
        self.axes = []
        for i in range(4):
            ax = self.fig.add_subplot(gs[i], sharex=None if i == 0 else self.axes[0])
            self.axes.append(ax)
        self.ax_p, self.ax_rsi, self.ax_macd, self.ax_vol = self.axes
        
        # Optimized margins for the signal analysis box
        plt.subplots_adjust(bottom=0.08, top=0.94, left=0.05, right=0.74)
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        ui_bg = '#121212'
        self.txt_ticker = TextBox(plt.axes([0.05, 0.01, 0.07, 0.035], facecolor=ui_bg), 'CODE ', initial=self.ticker, color=ui_bg)
        self.txt_ticker.text_disp.set_color(C_NEON_BLUE)
        self.txt_ticker.on_submit(self.on_submit)
        
        self.btns = []
        for i, (l, iv, p) in enumerate([('1D','1d','1y'), ('1W','1wk','2y'), ('1M','1mo','5y')]):
            b = Button(plt.axes([0.13 + i*0.04, 0.01, 0.03, 0.035], facecolor=ui_bg), l, color=ui_bg)
            b.label.set_color('white')
            b.label.set_fontsize(9)
            b.on_clicked(lambda e, iv=iv, p=p: self.set_params(iv, p))
            self.btns.append(b)
            
        self.btn_mode = Button(plt.axes([0.26, 0.01, 0.12, 0.035], facecolor=ui_bg), f'SKILL: {self.mode[:10]}', color=ui_bg)
        self.btn_mode.label.set_color(C_NEON_PURPLE)
        self.btn_mode.label.set_fontsize(9)
        self.btn_mode.on_clicked(self.toggle_mode)

    def on_submit(self, t): self.ticker = t.upper(); self.refresh()
    def set_params(self, iv, p): self.interval, self.period = iv, p; self.refresh()
    def toggle_mode(self, e):
        modes = ["STANDARD", "ELLIOTT", "MONTE CARLO", "SUMMARY"]
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
        self.btn_mode.label.set_text(f"SKILL: {self.mode[:10]}")
        self.refresh()

    def draw_candles(self, df: pd.DataFrame) -> None:
        width = 0.5 if self.interval == '1d' else 2.0
        up = df[df.Close >= df.Open]
        dn = df[df.Close < df.Open]
        self.ax_p.vlines(df.index, df.Low, df.High, color='#444444', lw=0.8)
        self.ax_p.bar(up.index, up.Close - up.Open, width, bottom=up.Open, color=C_UP, alpha=0.9, zorder=5)
        self.ax_p.bar(dn.index, dn.Open - dn.Close, width, bottom=dn.Close, color=C_DOWN, alpha=0.9, zorder=5)

    def draw_signal_analysis(self, df: pd.DataFrame, signals_count: int, extra_data: dict = None) -> None:
        """Enhanced Signal Analysis providing mode-specific metrics."""
        last_p = df['Close'].iloc[-1]
        last_rsi = df['RSI'].iloc[-1]
        
        # Base Confluence Logic
        status, saran, color = "NEUTRAL", "WAIT", "white"
        if last_rsi < 35: status, saran, color = "OVERSOLD", "BUY ON DIP", C_NEON_BLUE
        elif last_rsi > 65: status, saran, color = "OVERBOUGHT", "TAKE PROFIT", C_DOWN
        elif signals_count > 0: status, saran, color = "DIVERGENCE", "ACCUMULATE", C_UP

        # Build Info Text
        info = (
            f"--- SIGNAL ANALYZE ---\n"
            f"TICKER : {self.ticker}\n"
            f"PRICE  : {last_p:,.0f}\n"
            f"RSI    : {last_rsi:.1f}\n"
            f"----------------------\n"
            f"STATUS : {status}\n"
            f"SARAN  : {saran}\n"
            f"----------------------\n"
            f"MODE   : {self.mode}\n"
        )

        # Mode-Specific Enhancements
        if self.mode == "ELLIOTT" and extra_data:
            wave_num = extra_data.get('wave_count', 0)
            trend = "BULLISH" if wave_num % 2 != 0 else "CORRECTIVE"
            info += f"WAVE   : {wave_num} ({trend})\n"
            info += f"PIVOTS : {wave_num} FOUND\n"
        
        elif self.mode == "MONTE CARLO" and extra_data:
            avg = extra_data.get('mean', 0)
            p95 = extra_data.get('p95', 0)
            p05 = extra_data.get('p05', 0)
            info += f"EXPECT : {avg:,.0f}\n"
            info += f"P95 HI : {p95:,.0f}\n"
            info += f"P05 LO : {p05:,.0f}\n"
        
        elif self.mode == "SUMMARY":
            info += "CONSOLIDATED REPORT\n"
        
        else:
            info += f"SIGS   : {signals_count}\n"
            info += f"TARGET : {last_p * 1.1:,.0f}\n"
            info += f"STOP   : {last_p * 0.95:,.0f}\n"

        props = dict(boxstyle='round,pad=0.8', facecolor='#0d0d0d', alpha=0.95, edgecolor=color, lw=1.5)
        self.ax_p.text(1.03, 1.0, info, transform=self.ax_p.transAxes, color='white', 
                      family='monospace', fontsize=10, verticalalignment='top', bbox=props)

    def refresh(self) -> None:
        try:
            df = AnalyticsEngine.fetch_data(self.ticker, self.period, self.interval)
            if df.empty: return
            
            plt.rcParams.update({'font.size': 10, 'font.weight': 'normal'})

            for ax in self.axes: 
                ax.clear(); ax.grid(True, color=C_GRID, linestyle=':', alpha=0.5)
                ax.tick_params(colors='gray', labelsize=8)

            sig_total = 0
            extra_analysis = {}

            if self.mode != "SUMMARY":
                self.draw_candles(df)
                
                if self.mode == "STANDARD":
                    sigs = AnalyticsEngine.get_divergence(df)
                    sig_total = len(sigs)
                    for s in sigs:
                        clr = C_UP if s.type=='BULLISH' else C_DOWN
                        self.ax_p.plot([s.d1, s.d2], [s.p1, s.p2], color=clr, lw=2.5, marker='o', markersize=4, zorder=6)
                
                elif self.mode == "ELLIOTT":
                    px, py = AnalyticsEngine.get_zigzag(df)
                    if len(py) >= 2:
                        self.ax_p.plot(px, py, color=C_NEON_BLUE, ls='--', lw=1.2, alpha=0.7)
                        labels = ['1','2','3','4','5','A','B','C']
                        for i in range(min(len(py), 8)):
                            self.ax_p.text(px[i], py[i], labels[i], color='white', weight='bold', fontsize=9,
                                         ha='center', va='center', bbox=dict(boxstyle='circle,pad=0.2', fc=C_NEON_BLUE, ec='none'))
                        extra_analysis['wave_count'] = len(py)
                
                elif self.mode == "MONTE CARLO":
                    paths = AnalyticsEngine.run_monte_carlo(df)
                    if paths.any():
                        fut_dates = pd.date_range(df.index[-1], periods=40, freq=df.index[1] - df.index[0])
                        for i in range(paths.shape[1]):
                            self.ax_p.plot(fut_dates, paths[:, i], color=C_NEON_BLUE, alpha=0.03, lw=1)
                        extra_analysis['mean'] = np.mean(paths[-1])
                        extra_analysis['p95'] = np.percentile(paths[-1], 95)
                        extra_analysis['p05'] = np.percentile(paths[-1], 5)

                # INDICATORS
                self.ax_rsi.plot(df.index, df['RSI'], color=C_NEON_PURPLE, lw=1.2)
                self.ax_rsi.axhline(70, color=C_DOWN, lw=0.8, ls='--'); self.ax_rsi.axhline(30, color=C_UP, lw=0.8, ls='--')
                self.ax_rsi.set_ylim(0, 100)
                self.ax_rsi.set_ylabel("RSI", color='gray', fontsize=8)
                
                col_macdh = [c for c in df.columns if 'MACDh' in str(c)][0]
                m_colors = [C_UP if x >= 0 else C_DOWN for x in df[col_macdh]]
                self.ax_macd.bar(df.index, df[col_macdh], color=m_colors, alpha=0.7)
                self.ax_macd.set_ylabel("MACD", color='gray', fontsize=8)
                
                v_colors = [C_UP if c >= o else C_DOWN for o, c in zip(df.Open, df.Close)]
                self.ax_vol.bar(df.index, df['Volume'], color=v_colors, alpha=0.4)
                self.ax_vol.set_ylabel("VOL", color='gray', fontsize=8)
                
            else:
                # SUMMARY MODE: Run all analysis and display text
                sigs = AnalyticsEngine.get_divergence(df)
                px, py = AnalyticsEngine.get_zigzag(df)
                paths = AnalyticsEngine.run_monte_carlo(df)
                last_p = df['Close'].iloc[-1]
                last_rsi = df['RSI'].iloc[-1]
                
                # Turn off grids and ticks for clean text view
                for ax in self.axes: ax.axis('off')
                
                # Dynamic Elliott Wave Targets based on Fibonacci
                bull_tgt, bull_max, bear_sup, bear_max = last_p * 1.08, last_p * 1.15, last_p * 0.92, last_p * 0.85
                if len(py) >= 2:
                    swing = abs(py[-1] - py[-2]) if abs(py[-1] - py[-2]) > 0 else last_p * 0.1
                    if len(py) % 2 != 0: # Impulsive
                        bull_tgt, bull_max = py[-1] + (swing * 0.618), py[-1] + swing
                        bear_sup, bear_max = py[-1] - (swing * 0.382), py[-2]
                    else: # Corrective
                        bull_tgt, bull_max = py[-1] + (swing * 0.5), py[-2]
                        bear_sup, bear_max = py[-1] - (swing * 0.236), py[-1] - (swing * 0.618)
                
                summary_text = (
                    f"=== MASTER STRATEGY SUMMARY: {self.ticker} ===\n\n"
                    f"1. MOMENTUM & DIVERGENCE (STANDARD)\n"
                    f"   - Current Price: {last_p:,.0f} | RSI: {last_rsi:.1f}\n"
                    f"   - Divergence Signals Found: {len(sigs)}\n"
                    f"   - Sentiment: {'BULLISH REVERSAL' if any(s.type=='BULLISH' for s in sigs) else 'NEUTRAL/BEARISH'}\n\n"
                    f"2. MARKET STRUCTURE (ELLIOTT WAVE)\n"
                    f"   - Detected Wave Count: {len(py)}\n"
                    f"   - Current Phase: {'Impulsive (Trend)' if len(py)%2 != 0 else 'Corrective (Bounce)'}\n"
                    f"   - Key Structure: Structural ZigZag confirms {len(py)} major pivots.\n"
                    f"   - Bullish Scenario: Most Likely Target ~{bull_tgt:,.0f} | Overshoot ~{bull_max:,.0f}\n"
                    f"   - Bearish Scenario: Most Likely Support ~{bear_sup:,.0f} | Max Support ~{bear_max:,.0f}\n\n"
                    f"3. PROBABILISTIC FORECAST (MONTE CARLO)\n"
                )
                
                if paths.any():
                    mean_p = np.mean(paths[-1])
                    p95 = np.percentile(paths[-1], 95)
                    p05 = np.percentile(paths[-1], 5)
                    summary_text += (
                        f"   - Expected Price (40 periods): {mean_p:,.0f}\n"
                        f"   - Optimistic Target (P95): {p95:,.0f}\n"
                        f"   - Pessimistic Floor (P05): {p05:,.0f}\n"
                        f"   - Projected Drift: {((mean_p/last_p)-1)*100:+.2f}%\n\n"
                    )
                
                summary_text += (
                    f"4. FINAL EXECUTIVE VERDICT\n"
                    f"   - Primary Recommendation: {'ACCUMULATE' if last_rsi < 40 or len(sigs)>0 else 'HOLD/WAIT'}\n"
                    f"   - Risk Profile: {'HIGH' if last_rsi > 60 else 'MODERATE'}\n"
                    f"   - Technical Confluence: {'STRONG' if (len(sigs)>0 and last_rsi<40) else 'LOW'}\n"
                )

                self.ax_p.text(0.05, 0.95, summary_text, transform=self.ax_p.transAxes, 
                              color='white', family='monospace', fontsize=12, verticalalignment='top',
                              linespacing=1.6)

            # UPDATED ANALYSIS (Right box)
            self.draw_signal_analysis(df, sig_total, extra_analysis)
            self.ax_p.set_title(f"BOT GEMINI TERMINAL | {self.ticker}", loc='left', color='white', weight='bold', fontsize=12)
            
            plt.draw()
            
            # Standardized filename
            safe_mode = self.mode.replace(" ", "_")
            filename = f"captures/{self.ticker}_{self.interval}_{safe_mode}.png"
            self.fig.savefig(os.path.join("geminiV2", filename), facecolor=C_BG)
            print(f"✔ Chart Updated: {filename}")
            
        except Exception as e: print(f"ERROR: {e}")

if __name__ == "__main__":
    app = BotGeminiTerminal()
    plt.show()
