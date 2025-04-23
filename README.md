# Crypto Assistant 🤖

A sophisticated cryptocurrency trading assistant that combines a comprehensive knowledge base with real-time market data and analysis capabilities.

## 🌟 Features

### Knowledge Base Integration
- Extensive trading psychology insights
- Technical analysis strategies
- Risk management principles
- Position sizing methodologies
- Market indicators and analysis
- Blockchain fundamentals

### Real-time Capabilities
- Latest cryptocurrency news
- Market signals and analysis
- Price tracking and monitoring
- Technical indicator analysis

### User Experience
- Persistent chat memory using Supabase
- Export chat history (PDF/TXT)
- Clean and intuitive interface
- Secure authentication

## 📚 Knowledge Base Sources

The assistant is powered by a rich knowledge base including:

- Bitcoin fundamentals
- Trading psychology masterclass
- Risk management strategies
- Position sizing techniques
- Technical analysis indicators
- Ethereum whitepaper
- Trading strategies
- Market analysis methodologies

## 💬 Ask Me About

### 🧠 Strategy & Psychology
- FOMO in crypto trading
- Dollar-cost averaging
- Bull market biases

### 📊 Crypto Analysis
- RSI & MACD for Solana
- Should I buy Ethereum?
- Technical trends for Bitcoin

### 📰 Latest News
- What's new with Bitcoin?
- Crypto ETF updates
- Regulation buzz

### 💡 General
- Bull vs. bear markets
- How hardware wallets work
- What is blockchain?

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Supabase account
- OpenAI API key
- NewsAPI key (for cryptocurrency news)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crypto-assistant.git
cd crypto-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
NEWSAPI_KEY=your_newsapi_key
```

### Initial Setup

1. Ingest the knowledge base (if not already done):
```bash
python ingestion.py
```

2. Run the application:
```bash
streamlit run app.py
```

## 🏗️ Project Structure

```
crypto-assistant/
├── app.py                 # Main application
├── ingestion.py           # Knowledge base ingestion
├── requirements.txt       # Project dependencies
├── .env                  # Environment variables
├── assets/               # Static assets
├── chains/               # LangChain components
├── database/             # Database operations
├── frontend/             # UI components
├── knowledge_base/       # Source documents
├── logs/                 # Application logs
├── pages/                # Streamlit pages
└── utils/                # Utility functions
```

## 🔧 Configuration

The application can be configured through environment variables:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `NEWSAPI_KEY`: Your NewsAPI key for cryptocurrency news
- `LOG_LEVEL`: Application log level (default: INFO)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for the language model capabilities
- Supabase for the database infrastructure
- Streamlit for the web interface framework
- All knowledge base contributors and authors 