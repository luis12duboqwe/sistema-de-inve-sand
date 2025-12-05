# AI-Powered Sales Forecasting & Predictive Restocking

## Overview

Stellar Inventory now includes advanced AI-powered sales forecasting and predictive restocking alerts. The system analyzes your sales history to predict future demand, estimate when products will run out of stock, and recommend optimal reorder quantities.

## Key Features

### 1. Sales Forecasting

The forecasting engine analyzes 90 days of sales history to predict:
- **Average Daily Sales**: Calculated from the last 30 days with trend adjustments
- **7-Day Sales Projection**: Short-term demand forecast for immediate planning
- **30-Day Sales Projection**: Long-term forecast for strategic inventory decisions
- **Days Until Stockout**: Estimated time before product runs out based on current velocity
- **Trend Detection**: Identifies whether sales are increasing, stable, or decreasing

### 2. Intelligent Recommendations

Each product receives:
- **Restock Quantity**: Recommended order amount including 14-day safety stock
- **Confidence Score**: Reliability indicator based on historical data availability
- **Growth Adjustment**: Predictions factor in sales acceleration or deceleration
- **Stock Status**: Clear indication of urgency level and timeline

### 3. Predictive Alerts

Automatic alerts for products that need attention:
- **Critical (Red)**: Stock will run out in ≤3 days or already at zero
- **High (Orange)**: Stock will run out in ≤7 days
- **Medium (Yellow)**: Stock will run out in ≤14 days
- **Low (Gray)**: Preventive restock recommended

Each alert includes:
- Current stock level
- Days until stockout
- Recommended order quantity
- Estimated restock date (accounting for 7-day lead time)
- Reasoning explanation

### 4. AI-Generated Insights

GPT-4 powered analysis provides:
- 3-5 actionable business recommendations
- Context-aware inventory optimization suggestions
- Sales opportunity identification
- Risk mitigation strategies

## How It Works

### Forecasting Methodology

1. **Data Collection**
   - Recent sales: Last 30 days (weighted heavily)
   - Historical sales: 31-90 days ago (for trend comparison)
   - Only non-cancelled orders with non-promotional items

2. **Velocity Calculation**
   - Recent daily sales = Total sold in 30 days / 30
   - Historical daily sales = Total sold in days 31-90 / 60
   - Current velocity used as baseline for predictions

3. **Trend Detection**
   - Increasing: Recent sales > 15% higher than historical
   - Decreasing: Recent sales > 15% lower than historical
   - Stable: Within ±15% variance

4. **Growth Factor Application**
   - Increasing trend: Apply 0-30% growth multiplier (capped)
   - Decreasing trend: Apply 0-20% decline multiplier (limited)
   - Stable trend: No adjustment (1.0x multiplier)

5. **Stockout Prediction**
   - Days until stockout = Current stock / Predicted daily sales
   - Accounts for growth trends in calculation
   - Shows ∞ for products with no predicted sales

6. **Restock Calculation**
   - Safety stock = 14 days × predicted daily sales
   - Recommended order = Safety stock + 30-day forecast - current stock
   - Never recommends negative quantities

### Confidence Scoring

Confidence reflects data reliability:
- **95%**: ≥20 historical orders
- **80%**: 10-19 historical orders
- **65%**: 5-9 historical orders
- **50%**: 2-4 historical orders
- **30%**: 0-1 historical orders

Low confidence forecasts are still useful but should be validated with business knowledge.

## Using the Feature

### Access Points

1. **Header Button**: Click the sparkle icon (or press Alt+F)
   - Shows red badge with critical alert count
   
2. **Dashboard Widget**: On the products tab
   - Displays summary metrics
   - Shows critical alerts count
   - Lists top performing products
   - "Generate Forecast" button if not yet created

### Forecast Dashboard Tabs

#### Summary Tab
- Total products analyzed
- Products needing restock
- Critical stock alerts
- Projected revenue (7-day and 30-day)
- Top performing products (increasing trend)
- Slow-moving products (low velocity, high stock)

#### Forecasts Tab
- Complete list of all product forecasts
- Sortable by stockout urgency
- Click any product to open edit dialog
- Shows confidence score for each prediction
- Displays trend indicators

#### Alerts Tab
- Only products requiring attention
- Sorted by urgency (critical → low)
- Color-coded border by urgency level
- Reasoning explanation for each alert
- Recommended restock date

#### Insights Tab
- AI-generated business recommendations
- Methodology explanation
- Regenerate button for fresh analysis

### Best Practices

1. **Regular Updates**: Regenerate forecasts weekly or after major sales events
2. **Review Critical Alerts**: Check daily for products at risk of stockout
3. **Validate Low Confidence**: Double-check recommendations when confidence <65%
4. **Consider Seasonality**: AI detects trends but may not predict seasonal spikes
5. **Adjust Lead Times**: Default 7-day lead time may need adjustment for your suppliers
6. **Safety Stock**: 14-day buffer is conservative; adjust if you have reliable suppliers

### Keyboard Shortcut

- **Alt + F**: Open AI forecasting dialog

## Technical Details

### Data Storage

Forecasts are cached in browser storage:
- `forecasting_data`: Array of product forecasts
- `forecasting_alerts`: Array of restock alerts
- `forecasting_summary`: Aggregate statistics
- `forecasting_last_updated`: Timestamp of last generation

Cache expires after 24 hours and prompts for regeneration.

### Performance

- Initial forecast generation: 5-15 seconds (depends on data volume)
- Subsequent views: Instant (uses cached data)
- AI insights generation: 3-8 seconds (calls GPT-4)
- Maximum products analyzed: No limit, but UI shows top 50 in forecasts tab

### Privacy & Data

- All calculations run client-side in your browser
- Only anonymized data sent to OpenAI for insights (product names, metrics)
- No personal customer information shared with AI
- Forecasts stored locally, not on external servers

## Limitations

1. **Historical Data Required**: Needs order history for accurate predictions
2. **Trend Continuity**: Assumes current trends continue (can't predict disruptions)
3. **No External Factors**: Doesn't account for promotions, seasonality, market changes
4. **Single Profile**: Generates forecast for one profile at a time
5. **Lead Time Assumption**: Uses fixed 7-day supplier lead time

## Troubleshooting

### "No forecasts generated"
- Ensure you have products in the system
- Check that you have some order history
- Verify a profile is selected (not "all")

### "Low confidence scores"
- Normal for new products or limited sales history
- Build history over time for better predictions
- Use business judgment to validate recommendations

### "AI insights unavailable"
- Check internet connection (required for GPT-4)
- Forecasts still work without insights
- Try regenerating if initial attempt failed

### "Forecast seems inaccurate"
- Review the confidence score
- Check if recent promotions skewed data
- Verify order dates are correct
- Consider external factors AI can't detect

## Future Enhancements

Planned improvements:
- Seasonality detection and adjustment
- Multi-profile comparison dashboard
- Custom lead time configuration per supplier
- Email/SMS alerts for critical stockouts
- Integration with purchase orders
- Export forecasts to CSV/PDF
- Historical forecast accuracy tracking

## Support

For questions or issues with AI forecasting:
1. Review this documentation
2. Check the methodology section in the Insights tab
3. Verify your sales data is accurate
4. Consider starting with manual review of critical alerts before automating decisions

---

**Version**: 1.0  
**Last Updated**: January 2025  
**Feature Status**: Production Ready
