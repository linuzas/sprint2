# utils/tools_v2.py
import requests
import os
import streamlit as st
from datetime import datetime, timedelta
from newsapi import NewsApiClient
import numpy as np
import pandas as pd
import json


newsapi_key = st.secrets["newsapi_key"]

def get_crypto_news_newsapi(query: str) -> str:
    """
    Fetch the latest crypto-related news based on the user's query.
    """
    try:
        newsapi = NewsApiClient(api_key=newsapi_key)
        from_date = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

        # Simple keyword fallback if query is empty
        search_term = query.strip() if query else "cryptocurrency OR bitcoin OR ethereum OR blockchain"

        response = newsapi.get_everything(
            q=search_term,
            from_param=from_date,
            to=to_date,
            language="en",
            sort_by="publishedAt",
            page_size=5
        )

        articles = response.get("articles", [])
        if not articles:
            return f"No news found for: **{query}**."

        result = f"📰 News for: **{query}**\n\n"
        for a in articles:
            result += f"**{a['title']}**\n"
            if a.get("description"):
                result += f"{a['description']}\n"
            result += f"[Read more →]({a['url']})\n\n"
        return result.strip()
    except Exception as e:
        return f"❌ Error retrieving news: {e}"

def get_crypto_price_gecko(symbol: str) -> str:
    """
    Fetch the current USD price for a given crypto symbol via CoinGecko public API.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": symbol.lower(), "vs_currencies": "usd"}
    resp = requests.get(url, params=params, timeout=5)
    resp.raise_for_status()
    data = resp.json()
    price = data.get(symbol.lower(), {}).get("usd")
    if price is None:
        return "Symbol not supported"
    return f"{price:,.2f} USD"

# Common symbol mappings to CoinGecko IDs
SYMBOL_TO_COINGECKO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "doge": "dogecoin",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "dot": "polkadot",
    "ltc": "litecoin",
    "link": "chainlink",
    # Add more as needed
}

# Function schema for OpenAI function calling
GET_PRICE_GEO_SCHEMA = {
    "name": "get_crypto_price_gecko",
    "description": (
        "Get the current USD price for a cryptocurrency via CoinGecko. "
        "The `symbol` parameter must be the CoinGecko asset id—"
        "for example 'bitcoin', 'ethereum', or 'dogecoin'—"
        "not the ticker like 'btc' or 'eth'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": (
                    "The CoinGecko asset id, e.g. 'bitcoin', 'ethereum', or 'dogecoin'."
                ),
            }
        },
        "required": ["symbol"],
    },
}

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period, min_periods=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def calculate_bollinger_bands(prices, window=20, num_std=2):
    sma = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, sma, lower_band

def calculate_price_change(prices):
    last_price = prices.iloc[-1]
    day_change = ((last_price / prices.iloc[-24]) - 1) * 100 if len(prices) >= 24 else None
    week_change = ((last_price / prices.iloc[-168]) - 1) * 100 if len(prices) >= 168 else None
    return day_change, week_change

def get_crypto_signals(symbol="bitcoin", days=14, currency="usd"):
    """
    Get comprehensive trading signals and technical analysis for a cryptocurrency.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {
        "vs_currency": currency,
        "days": days
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        prices = data.get("prices", [])
        volumes = data.get("total_volumes", [])
        market_caps = data.get("market_caps", [])
        
        if not prices:
            return {"error": "No price data returned."}

        # Create and process the dataframe
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        time_deltas = df.index.to_series().diff().dropna()
        most_common_delta = time_deltas.value_counts().idxmax()

        if most_common_delta <= pd.Timedelta(hours=1):
            data_frequency = "hourly"
        elif most_common_delta <= pd.Timedelta(days=1):
            data_frequency = "daily"
        else:
            data_frequency = f"every {most_common_delta}"
        # Add volume data if available
        if volumes:
            vol_df = pd.DataFrame(volumes, columns=["timestamp", "volume"])
            vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
            vol_df.set_index("timestamp", inplace=True)
            df["volume"] = vol_df["volume"]
        
        # Add market cap data if available
        if market_caps:
            mc_df = pd.DataFrame(market_caps, columns=["timestamp", "market_cap"])
            mc_df["timestamp"] = pd.to_datetime(mc_df["timestamp"], unit="ms")
            mc_df.set_index("timestamp", inplace=True)
            df["market_cap"] = mc_df["market_cap"]

        # Calculate indicators
        df["SMA20"] = df["price"].rolling(window=20).mean()
        df["SMA50"] = df["price"].rolling(window=50).mean()
        df["SMA200"] = df["price"].rolling(window=200).mean() if len(df) >= 200 else None
        df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = calculate_bollinger_bands(df["price"])
        df["RSI"] = calculate_rsi(df["price"], period=14)
        df["MACD"], df["MACD_Signal"] = calculate_macd(df["price"])
        df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]
        
        if "volume" in df.columns:
            df["Volume_SMA20"] = df["volume"].rolling(window=20).mean()
            df["Volume_Change"] = df["volume"].pct_change() * 100
        
        df["Volatility"] = df["price"].rolling(window=20).std() / df["price"].rolling(window=20).mean() * 100

        # Get latest values
        current_price = df["price"].iloc[-1]
        day_change, week_change = calculate_price_change(df["price"])
        latest_values = df.iloc[-1].to_dict()
        
        # Calculate additional metrics
        current_volatility = latest_values.get("Volatility")
        price_vs_sma20 = (current_price / latest_values.get("SMA20") - 1) * 100 if not pd.isna(latest_values.get("SMA20")) else None
        price_vs_sma50 = (current_price / latest_values.get("SMA50") - 1) * 100 if not pd.isna(latest_values.get("SMA50")) else None
        
        # BB Position
        if not pd.isna(latest_values.get("BB_Upper")) and not pd.isna(latest_values.get("BB_Lower")):
            bb_range = latest_values.get("BB_Upper") - latest_values.get("BB_Lower")
            if bb_range != 0:
                bb_position = (current_price - latest_values.get("BB_Lower")) / bb_range
            else:
                bb_position = 0.5
        else:
            bb_position = None

        # Build signals object
        signals = {
            "symbol": symbol,
            "currency": currency,
            "days": days,
            "data_frequency": data_frequency,
            "current_price": round(current_price, 4),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "price_changes": {
                "24h": round(day_change, 2) if day_change is not None else None,
                "7d": round(week_change, 2) if week_change is not None else None,
            },
            "indicators": {
                "SMA20": round(latest_values.get("SMA20", 0), 4) if not pd.isna(latest_values.get("SMA20")) else None,
                "SMA50": round(latest_values.get("SMA50", 0), 4) if not pd.isna(latest_values.get("SMA50")) else None,
                "SMA200": round(latest_values.get("SMA200", 0), 4) if latest_values.get("SMA200") is not None and not pd.isna(latest_values.get("SMA200")) else None,
                "RSI": round(latest_values.get("RSI", 0), 2) if not pd.isna(latest_values.get("RSI")) else None,
                "MACD": round(latest_values.get("MACD", 0), 4) if not pd.isna(latest_values.get("MACD")) else None,
                "MACD_Signal": round(latest_values.get("MACD_Signal", 0), 4) if not pd.isna(latest_values.get("MACD_Signal")) else None,
                "MACD_Histogram": round(latest_values.get("MACD_Histogram", 0), 4) if not pd.isna(latest_values.get("MACD_Histogram")) else None,
                "BB_Upper": round(latest_values.get("BB_Upper", 0), 4) if not pd.isna(latest_values.get("BB_Upper")) else None,
                "BB_Middle": round(latest_values.get("BB_Middle", 0), 4) if not pd.isna(latest_values.get("BB_Middle")) else None,
                "BB_Lower": round(latest_values.get("BB_Lower", 0), 4) if not pd.isna(latest_values.get("BB_Lower")) else None,
                "BB_Position": round(bb_position, 2) if bb_position is not None else None,
                "Volatility": round(current_volatility, 2) if current_volatility is not None and not pd.isna(current_volatility) else None,
                "Price_vs_SMA20": round(price_vs_sma20, 2) if price_vs_sma20 is not None else None,
                "Price_vs_SMA50": round(price_vs_sma50, 2) if price_vs_sma50 is not None else None,
            },
            "signals": [],
            "market_data": {}
        }

        # Add volume and market cap data if available
        if "volume" in df.columns:
            signals["market_data"]["volume_24h"] = round(latest_values.get("volume", 0), 2) if not pd.isna(latest_values.get("volume")) else None
            signals["market_data"]["volume_sma20"] = round(latest_values.get("Volume_SMA20", 0), 2) if not pd.isna(latest_values.get("Volume_SMA20")) else None
            signals["market_data"]["volume_change"] = round(latest_values.get("Volume_Change", 0), 2) if not pd.isna(latest_values.get("Volume_Change")) else None
        
        if "market_cap" in df.columns:
            signals["market_data"]["market_cap"] = round(latest_values.get("market_cap", 0), 2) if not pd.isna(latest_values.get("market_cap")) else None

        # Generate signals
        # SMA Signals
        if not pd.isna(latest_values.get("SMA20")) and not pd.isna(latest_values.get("SMA50")):
            if latest_values.get("SMA20") > latest_values.get("SMA50") and df["SMA20"].iloc[-2] <= df["SMA50"].iloc[-2]:
                signals["signals"].append({"type": "BUY", "strength": "STRONG", "indicator": "SMA Crossover", "description": "SMA 20 crossed above SMA 50"})
            elif latest_values.get("SMA20") < latest_values.get("SMA50") and df["SMA20"].iloc[-2] >= df["SMA50"].iloc[-2]:
                signals["signals"].append({"type": "SELL", "strength": "STRONG", "indicator": "SMA Crossover", "description": "SMA 20 crossed below SMA 50"})

        # RSI Signals
        rsi = latest_values.get("RSI")
        if not pd.isna(rsi):
            if rsi < 30:
                signals["signals"].append({"type": "BUY", "strength": "MEDIUM", "indicator": "RSI", "description": f"RSI oversold at {round(rsi, 2)}"})
            elif rsi < 40 and df["RSI"].iloc[-2] < 30:
                signals["signals"].append({"type": "BUY", "strength": "WEAK", "indicator": "RSI", "description": "RSI recovering from oversold"})
            elif rsi > 70:
                signals["signals"].append({"type": "SELL", "strength": "MEDIUM", "indicator": "RSI", "description": f"RSI overbought at {round(rsi, 2)}"})
            elif rsi > 60 and df["RSI"].iloc[-2] > 70:
                signals["signals"].append({"type": "SELL", "strength": "WEAK", "indicator": "RSI", "description": "RSI falling from overbought"})

        # MACD Signals
        macd = latest_values.get("MACD")
        macd_signal = latest_values.get("MACD_Signal")
        macd_hist = latest_values.get("MACD_Histogram")
        
        if not pd.isna(macd) and not pd.isna(macd_signal):
            if macd > macd_signal and df["MACD"].iloc[-2] <= df["MACD_Signal"].iloc[-2]:
                signals["signals"].append({"type": "BUY", "strength": "STRONG", "indicator": "MACD", "description": "MACD bullish crossover"})
            elif macd < macd_signal and df["MACD"].iloc[-2] >= df["MACD_Signal"].iloc[-2]:
                signals["signals"].append({"type": "SELL", "strength": "STRONG", "indicator": "MACD", "description": "MACD bearish crossover"})
            elif not pd.isna(macd_hist) and macd > 0 and macd_signal > 0 and macd_hist > 0 and macd_hist > df["MACD_Histogram"].iloc[-2]:
                signals["signals"].append({"type": "BUY", "strength": "WEAK", "indicator": "MACD", "description": "MACD histogram increasing in positive territory"})
            elif not pd.isna(macd_hist) and macd < 0 and macd_signal < 0 and macd_hist < 0 and macd_hist < df["MACD_Histogram"].iloc[-2]:
                signals["signals"].append({"type": "SELL", "strength": "WEAK", "indicator": "MACD", "description": "MACD histogram decreasing in negative territory"})

        # Bollinger Band Signals
        if not pd.isna(latest_values.get("BB_Upper")) and not pd.isna(latest_values.get("BB_Lower")):
            if current_price <= latest_values.get("BB_Lower"):
                signals["signals"].append({"type": "BUY", "strength": "MEDIUM", "indicator": "Bollinger Bands", "description": "Price at/below lower Bollinger Band"})
            elif current_price >= latest_values.get("BB_Upper"):
                signals["signals"].append({"type": "SELL", "strength": "MEDIUM", "indicator": "Bollinger Bands", "description": "Price at/above upper Bollinger Band"})

        # Volume Signals
        if "volume" in df.columns and "Volume_SMA20" in df.columns:
            vol = latest_values.get("volume")
            vol_sma = latest_values.get("Volume_SMA20")
            if not pd.isna(vol) and not pd.isna(vol_sma) and vol > vol_sma * 1.5:
                # High volume signal - check if this confirms price action
                if current_price > df["price"].iloc[-2]:
                    signals["signals"].append({"type": "BUY", "strength": "MEDIUM", "indicator": "Volume", "description": "High volume confirming upward price movement"})
                elif current_price < df["price"].iloc[-2]:
                    signals["signals"].append({"type": "SELL", "strength": "MEDIUM", "indicator": "Volume", "description": "High volume confirming downward price movement"})

        # Fallback signal if none found
        if not signals["signals"]:
            if not pd.isna(latest_values.get("SMA20")) and not pd.isna(latest_values.get("SMA50")) and not pd.isna(macd) and not pd.isna(macd_signal):
                if latest_values.get("SMA20") > latest_values.get("SMA50") and macd > macd_signal:
                    signals["signals"].append({
                        "type": "BULLISH_TREND",
                        "strength": "MEDIUM",
                        "indicator": "Combined Analysis",
                        "description": "Positive trend based on multiple indicators"
                    })
                elif latest_values.get("SMA20") < latest_values.get("SMA50") and macd < macd_signal:
                    signals["signals"].append({
                        "type": "BEARISH_TREND",
                        "strength": "MEDIUM",
                        "indicator": "Combined Analysis",
                        "description": "Negative trend based on multiple indicators"
                    })
                else:
                    signals["signals"].append({
                        "type": "NEUTRAL",
                        "strength": "WEAK",
                        "indicator": "Combined Analysis",
                        "description": "No strong signals detected"
                    })

        # Calculate overall sentiment
        buy_signals = [s for s in signals["signals"] if s["type"] == "BUY"]
        sell_signals = [s for s in signals["signals"] if s["type"] == "SELL"]
        
        if len(buy_signals) > len(sell_signals):
            overall_sentiment = "BULLISH"
        elif len(sell_signals) > len(buy_signals):
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"
        
        signals["overall_sentiment"] = overall_sentiment
        
        # Add support and resistance levels
        if len(df) >= 20:
            recent_high = df["price"].iloc[-20:].max()
            recent_low = df["price"].iloc[-20:].min()
            
            signals["price_levels"] = {
                "support": round(recent_low, 4),
                "resistance": round(recent_high, 4)
            }

        # Generate analysis summary
        summary = generate_analysis_summary(signals, df)
        signals["analysis_summary"] = summary
        
        # Format as markdown for the chatbot
        markdown_output = format_signals_markdown(signals)
        return markdown_output

    except Exception as e:
        return f"Error analyzing {symbol}: {str(e)}"

def generate_analysis_summary(signals, df):
    """Generate a detailed narrative of the technical analysis"""
    price = signals["current_price"]
    indicators = signals["indicators"]
    
    # Initialize summary
    summary = {
        "price_action": "",
        "trend_analysis": "", 
        "momentum_analysis": "",
        "volatility_analysis": "",
        "key_takeaways": []
    }
    
    # Price action summary
    day_change = signals["price_changes"]["24h"]
    week_change = signals["price_changes"]["7d"]
    
    price_action = f"Price is currently at {price} {signals['currency'].upper()}"
    if day_change is not None:
        price_action += f", {day_change:.2f}% {'up' if day_change > 0 else 'down'} in the last 24 hours"
    if week_change is not None:
        price_action += f" and {week_change:.2f}% {'up' if week_change > 0 else 'down'} over the past week"
    summary["price_action"] = price_action
    
    # Trend analysis
    trend_text = ""
    sma20 = indicators["SMA20"]
    sma50 = indicators["SMA50"]
    sma200 = indicators["SMA200"]
    
    if sma20 and sma50:
        if price > sma20 > sma50:
            trend_text = "Strong uptrend with price above both SMA20 and SMA50"
        elif price > sma20 and sma20 < sma50:
            trend_text = "Potential trend reversal with price above SMA20 but SMA20 below SMA50"
        elif price < sma20 and sma20 > sma50:
            trend_text = "Short-term weakness in an uptrend (price below SMA20 but SMA20 above SMA50)"
        elif price < sma20 < sma50:
            trend_text = "Strong downtrend with price below both SMA20 and SMA50"
    
    if sma200 is not None:
        if price > sma200:
            trend_text += ". Price is above SMA200, indicating a long-term bullish bias"
        else:
            trend_text += ". Price is below SMA200, indicating a long-term bearish bias"
    
    summary["trend_analysis"] = trend_text
    
    # Momentum analysis
    rsi = indicators["RSI"]
    macd = indicators["MACD"]
    macd_signal = indicators["MACD_Signal"]
    
    momentum_text = ""
    if rsi is not None:
        if rsi < 30:
            momentum_text = f"RSI at {rsi:.2f} indicates oversold conditions"
        elif rsi > 70:
            momentum_text = f"RSI at {rsi:.2f} indicates overbought conditions"
        else:
            momentum_text = f"RSI at {rsi:.2f} indicates neutral momentum"
    
    if macd is not None and macd_signal is not None:
        if momentum_text:
            momentum_text += ". "
        
        if macd > macd_signal:
            momentum_text += "MACD is above signal line, showing positive momentum"
        else:
            momentum_text += "MACD is below signal line, showing negative momentum"
    
    summary["momentum_analysis"] = momentum_text
    
    # Volatility analysis
    volatility = indicators["Volatility"]
    bb_position = indicators["BB_Position"]
    
    volatility_text = ""
    if volatility is not None:
        volatility_text = f"Current volatility is {volatility:.2f}%"
        if volatility > 5:
            volatility_text += ", indicating high market volatility"
        elif volatility < 2:
            volatility_text += ", indicating low market volatility"
        else:
            volatility_text += ", indicating moderate market volatility"
    
    if bb_position is not None:
        if volatility_text:
            volatility_text += ". "
        
        if bb_position < 0.2:
            volatility_text += "Price is near the lower Bollinger Band, suggesting potential overselling"
        elif bb_position > 0.8:
            volatility_text += "Price is near the upper Bollinger Band, suggesting potential overbuying"
        else:
            volatility_text += "Price is within the middle range of the Bollinger Bands"
    
    summary["volatility_analysis"] = volatility_text
    
    # Key takeaways
    for signal in signals["signals"]:
        summary["key_takeaways"].append(f"{signal['type']} signal ({signal['strength']}): {signal['description']}")
    
    # Add overall sentiment
    summary["key_takeaways"].append(f"Overall sentiment: {signals['overall_sentiment']}")
    
    return summary

def format_signals_markdown(signals):
    """Format signals as markdown for the chatbot"""
    if "error" in signals:
        return f"Error: {signals['error']}"

    # Build a markdown string
    md = f"# {signals['symbol'].upper()} Technical Analysis\n\n"
    md += f"**Symbol:** {signals['symbol'].upper()}  \n"
    md += f"**Time Period Analyzed:** Last {signals['days']} days ({signals['data_frequency']} data)\n\n"

    # Current price and changes
    md += f"**Current Price:** {signals['current_price']} {signals['currency'].upper()}\n"
    
    changes = signals['price_changes']
    change_text = []
    for period, change in changes.items():
        if change is not None:
            direction = "📈" if change > 0 else "📉"
            change_text.append(f"{period}: {change:+.2f}% {direction}")
    
    if change_text:
        md += f"**Price Changes:** {', '.join(change_text)}\n"
    
    # Market data
    if signals.get('market_data'):
        md += "\n## Market Data\n"
        for key, value in signals['market_data'].items():
            if value is not None:
                md += f"- **{key.replace('_', ' ').title()}:** {value:,.2f}\n"
    
    # Key indicators
    md += "\n## Key Indicators\n"
    
    # Trend indicators
    md += "\n### Trend\n"
    trend_indicators = ["SMA20", "SMA50", "SMA200", "Price_vs_SMA20", "Price_vs_SMA50"]
    for ind in trend_indicators:
        value = signals['indicators'].get(ind)
        if value is not None:
            md += f"- **{ind}:** {value}\n"
    
    # Momentum indicators
    md += "\n### Momentum\n"
    momentum_indicators = ["RSI", "MACD", "MACD_Signal", "MACD_Histogram"]
    for ind in momentum_indicators:
        value = signals['indicators'].get(ind)
        if value is not None:
            md += f"- **{ind}:** {value}\n"
    
    # Volatility indicators
    md += "\n### Volatility\n"
    volatility_indicators = ["BB_Upper", "BB_Middle", "BB_Lower", "BB_Position", "Volatility"]
    for ind in volatility_indicators:
        value = signals['indicators'].get(ind)
        if value is not None:
            md += f"- **{ind}:** {value}\n"
    
    # Trading signals
    md += "\n## Trading Signals\n"
    if signals["signals"]:
        for signal in signals["signals"]:
            signal_type = signal["type"]
            icon = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "⚪"
            md += f"{icon} **{signal_type}** ({signal['strength']}): {signal['indicator']} - {signal['description']}\n"
    else:
        md += "No specific trading signals detected\n"
    
    # Overall sentiment
    sentiment = signals["overall_sentiment"]
    sentiment_icon = "🟢" if sentiment == "BULLISH" else "🔴" if sentiment == "BEARISH" else "⚪"
    md += f"\n**Overall Sentiment:** {sentiment_icon} {sentiment}\n"
    
    # Support and resistance
    if "price_levels" in signals:
        md += "\n## Price Levels\n"
        md += f"- **Support:** {signals['price_levels']['support']}\n"
        md += f"- **Resistance:** {signals['price_levels']['resistance']}\n"
    
    # Analysis summary
    if "analysis_summary" in signals:
        md += "\n## Analysis Summary\n"
        summary = signals["analysis_summary"]
        
        md += f"\n**Price Action:**\n{summary['price_action']}\n"
        md += f"\n**Trend Analysis:**\n{summary['trend_analysis']}\n"
        md += f"\n**Momentum Analysis:**\n{summary['momentum_analysis']}\n" 
        md += f"\n**Volatility Analysis:**\n{summary['volatility_analysis']}\n"
        
        md += "\n**Key Takeaways:**\n"
        for i, takeaway in enumerate(summary["key_takeaways"], 1):
            md += f"{i}. {takeaway}\n"
    
    return md

GET_NEWS_NEWSAPI_SCHEMA = {
    "name": "get_crypto_news_newsapi",
    "description": "Fetch recent crypto news headlines related to a user query using NewsAPI.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's crypto-related news interest, e.g. 'Solana', 'Binance regulation', 'crypto ETFs'."
            }
        },
        "required": ["query"]
    }
}

GET_CRYPTO_SIGNALS_SCHEMA = {
    "name": "get_crypto_signals",
    "description": (
        "Get comprehensive trading signals and technical analysis for a cryptocurrency. "
        "Provides detailed technical indicators, trend analysis, and trading signals "
        "based on price movements and patterns."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": (
                    "The CoinGecko asset id, e.g. 'bitcoin', 'ethereum', or 'solana'. "
                    "Use the full name, not the ticker symbol."
                ),
            },
            "days": {
                "type": "integer",
                "description": "Number of days of historical data to analyze (default: 14)",
                "default": 14
            },
            "currency": {
                "type": "string",
                "description": "Currency for price data (default: 'usd')",
                "default": "usd"
            }
        },
        "required": ["symbol"]
    }
}

# Update your OPENAI_FUNCTIONS and TOOLS
OPENAI_FUNCTIONS = [GET_PRICE_GEO_SCHEMA, GET_NEWS_NEWSAPI_SCHEMA, GET_CRYPTO_SIGNALS_SCHEMA]

TOOLS = {
    "get_crypto_price_gecko": get_crypto_price_gecko,
    "get_crypto_news_newsapi": get_crypto_news_newsapi,
    "get_crypto_signals": get_crypto_signals
}