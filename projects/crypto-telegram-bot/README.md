# Crypto Analysis Telegram Bot

## 📌 Overview

A Telegram bot that provides real-time crypto price tracking and basic technical analysis using **CoinGecko API**.  
Built with Python and integrated into Telegram for interactive trading signals.  

## 🚀 Features

- `/price <token>` → Get real-time USD price  
- `/rsi <token>` → Calculate RSI (Relative Strength Index)  
- `/ma <token> <fast> <slow>` → EMA crossover check  
- `/signal <token>` → Generate BUY/SELL/HOLD signals using EMA + RSI  
- `/chart <token>` → Price chart with EMA indicators  

## 🛠 Tech Stack

- **Python 3**  
- **Telegram Bot API (python-telegram-bot)**  
- **CoinGecko API**  
- **Pandas, Numpy, Matplotlib**

## ▶️ Run Locally

1. Clone repository
2. Install dependencies:

   ```bash
   pip install requests pandas numpy matplotlib python-telegram-bot
