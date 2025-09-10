# Scalable Stock Price Prediction System

A comprehensive, automated system for predicting stock prices across 50 stocks using multiple LLM providers and FMP API data.

## 🚀 Features

- **50 Stocks Coverage**: Pre-configured for major stocks across Technology, Healthcare, Financial, Consumer, and Energy sectors
- **Multi-LLM Support**: OpenAI GPT, Anthropic Claude, Google Gemini, and DeepSeek
- **FMP API Integration**: Real-time analyst ratings, price targets, and financial data
- **Automated Scheduling**: Run predictions daily, weekly, or during market hours
- **Batch Processing**: Process multiple stocks concurrently with configurable limits
- **Customizable Prompts**: Tailored analysis for each stock and sector
- **Comprehensive Results**: JSON and CSV outputs with detailed analytics

## 📊 Stock Coverage

### Technology (10 stocks)
- AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, ADBE, CRM

### Healthcare (10 stocks)
- JNJ, PFE, UNH, ABBV, TMO, ABT, LLY, DHR, BMY, AMGN

### Financial (10 stocks)
- JPM, BAC, WFC, GS, MS, C, BLK, AXP, CB, SPGI

### Consumer (10 stocks)
- PG, KO, PEP, WMT, HD, MCD, DIS, NKE, SBUX, TGT

### Energy (10 stocks)
- XOM, CVX, COP, EOG, SLB, PSX, MPC, VLO, KMI, OKE

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd stock_agent_eval
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set environment variables**
```bash
export FMP_API_KEY="your_fmp_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"
export GOOGLE_API_KEY="your_google_api_key_here"
export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

## 🚀 Quick Start

### 1. Run Predictions for All Stocks
```bash
python manage_predictions.py run
```

### 2. Run Predictions for Specific Stocks
```bash
python manage_predictions.py run --symbols AAPL MSFT GOOGL
```

### 3. Run Single Stock Prediction
```bash
python manage_predictions.py run-single --single-symbol AAPL
```

### 4. Start Automated Scheduler
```bash
python manage_predictions.py start-scheduler
```

### 5. Check System Status
```bash
python manage_predictions.py status
```

### 6. List Configured Stocks
```bash
python manage_predictions.py list-stocks
```

## ⚙️ Configuration

### Stock Configuration (`stocks_config.json`)
Each stock has customizable settings:
- **FMP Data**: Enable/disable FMP API integration
- **LLM Providers**: Choose which AI models to use
- **Custom Prompts**: Sector-specific analysis requirements

### Scheduler Configuration (`scheduler_config.json`)
- **Schedule Type**: daily, weekly, market_hours, or custom
- **Market Hours**: Only run during trading hours
- **Concurrency**: Control processing speed
- **Retry Logic**: Automatic retry for failed predictions

## 📁 Output Structure

```
batch_predictions/
├── individual/           # Individual stock results
│   ├── AAPL_20250127_143022.json
│   ├── MSFT_20250127_143022.json
│   └── ...
├── summary/             # Batch summary reports
│   ├── batch_summary_20250127_143022.json
│   └── batch_summary_20250127_143022.csv
```

## 🔧 Customization

### Adding New Stocks
1. Edit `stocks_config.json`
2. Add new stock entry with symbol, name, sector
3. Customize prompt template and LLM providers

### Modifying Prompts
Each stock has a `custom_prompt_template` field for sector-specific analysis:
```json
{
  "symbol": "AAPL",
  "custom_prompt_template": "Focus on iPhone sales trends, services revenue growth, and China market dynamics."
}
```

### Changing LLM Providers
Modify the `llm_providers` array for each stock:
```json
"llm_providers": ["deepseek", "anthropic", "gemini", "openai"]
```

## 📈 Prediction Output Format

Each prediction includes:
- **Current Price**: Current market price
- **1-Day Target**: Tomorrow's predicted price
- **5-Day Target**: 5-day price prediction
- **30-Day Target**: 30-day price prediction
- **Confidence Level**: 0-100% confidence
- **Reasoning**: Detailed analysis and factors
- **FMP Data Used**: Whether FMP API data was incorporated

## 🕐 Scheduling Options

### Daily Schedule
- Run predictions every day at market open (9:30 AM ET)
- Configurable time and market hours restriction

### Weekly Schedule
- Run predictions on specific days of the week
- Useful for weekly analysis and reporting

### Market Hours Schedule
- Run predictions every hour during trading hours
- Real-time market monitoring

### Custom Schedule
- Define custom timing and frequency
- Multiple schedules per day

## 🔄 Automation Features

### Automatic Retry
- Failed predictions automatically retry up to 3 times
- Configurable retry intervals and limits

### Data Cleanup
- Automatic cleanup of old results (configurable retention)
- Daily cleanup at 2:00 AM

### Market Hours Detection
- Automatically detects market open/close
- Skips predictions during closed hours

### Concurrent Processing
- Process multiple stocks simultaneously
- Configurable concurrency limits (default: 5)

## 📊 Monitoring and Logging

### Log Files
- `scheduler.log`: Scheduler activity and errors
- Individual prediction logs in results directory

### Status Monitoring
```bash
python manage_predictions.py status
```
Shows:
- Current scheduler status
- Next scheduled run
- Market open/close status
- Configuration summary

## 🚨 Error Handling

### API Failures
- Graceful handling of API rate limits
- Automatic retry with exponential backoff
- Detailed error logging

### Network Issues
- Timeout handling for long-running requests
- Connection retry logic
- Fallback to cached data when available

### LLM Failures
- Individual provider failure isolation
- Continue processing with available providers
- Comprehensive error reporting

## 📈 Performance Optimization

### Batch Processing
- Process stocks in configurable batches
- Control memory usage and API rate limits

### Rate Limiting
- Built-in delays between API calls
- Respectful API usage patterns

### Caching
- FMP data caching to reduce API calls
- Configurable cache expiration

## 🔐 Security Considerations

### API Key Management
- Environment variable storage
- No hardcoded credentials
- Secure API key rotation

### Data Privacy
- Local storage of results
- No external data transmission
- Configurable data retention

## 🚀 Scaling Considerations

### Adding More Stocks
- Simply add entries to `stocks_config.json`
- System automatically scales to handle new stocks

### Performance Tuning
- Adjust `max_concurrent` for your system capabilities
- Monitor memory usage with large batches
- Consider running during off-peak hours

### Infrastructure
- Can run on cloud instances for 24/7 operation
- Docker support for containerized deployment
- Multiple instance support for high availability

## 📚 API Documentation

### FMP API Endpoints Used
- Price target news
- Analyst grades
- Company profiles
- Financial ratios

### LLM Provider APIs
- OpenAI GPT-4
- Anthropic Claude 3.5 Sonnet
- Google Gemini 2.0 Flash
- DeepSeek Chat

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify environment variables are set
   - Check API key validity and permissions

2. **Import Errors**
   - Ensure all requirements are installed
   - Check Python version compatibility

3. **Rate Limiting**
   - Reduce `max_concurrent` setting
   - Increase delays between API calls

4. **Memory Issues**
   - Process smaller batches
   - Monitor system resources

### Debug Mode
Enable detailed logging by modifying log levels in the scheduler configuration.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error details
3. Open an issue on GitHub
4. Check configuration files for errors

## 🔮 Future Enhancements

- **Real-time Alerts**: Email/Slack notifications for significant predictions
- **Performance Analytics**: Track prediction accuracy over time
- **Machine Learning**: Integrate ML models for improved accuracy
- **Web Dashboard**: Web-based monitoring and control interface
- **API Endpoints**: REST API for external integrations
- **Mobile App**: Mobile monitoring and alerts

---

**Note**: This system is designed for research and analysis purposes. Always conduct your own research and consider multiple sources before making investment decisions. 