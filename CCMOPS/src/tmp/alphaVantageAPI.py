from alpha_vantage.timeseries import TimeSeries

ts = TimeSeries(key='Y1HN9IQ3P463ABJ9', output_format='pandas')
data, meta_data = ts.get_intraday(symbol=['MSFT','AAPL'],interval='1min', outputsize='compact')

prices = data['4. close'].tail(1)

print(prices)

