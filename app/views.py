from django.http import JsonResponse
import json
import os
import pandas as pd
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from rest_framework.response import Response
from rest_framework import status
from .serializers import FinancialDataSerializer
from app.models import Price, Stock
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
import logging
from django.db import transaction
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
# Get the current directory
current_directory = os.path.dirname(__file__)

# Define the file name
# file_name = 'BMRI.JK.csv'

# Combine the directory and file name to create the file path
# file_path = os.path.join(current_directory, file_name)

@api_view(('POST','GET'))
def upload_csv(request):
    csv_file = request.FILES['csv_file']
    name = request.POST.get('name', 'Untitled')
    code = request.POST.get('code', 'Untitled')
    sector = request.POST.get('sector', 'Untitled')

    try:
        data_frame = pd.read_csv(csv_file)
    except Exception as e:
        return Response({'error': 'Error reading CSV file'}, status=status.HTTP_400_BAD_REQUEST)

    data_list = data_frame.to_dict('records')
    stock_instance = Stock.objects.create(name=name, code=code, sector=sector)
    
    for data_entry in data_list:
        mapped_data_entry = {
            'stock': stock_instance.pk, 
            'date': data_entry['Date'],
            'open': data_entry['Open'],
            'high': data_entry['High'],
            'low': data_entry['Low'],
            'close': data_entry['Close'],
            'volume': data_entry['Volume'],
        }
        serializer = FinancialDataSerializer(data=mapped_data_entry)
        
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'message': 'Data saved successfully'}, status=status.HTTP_201_CREATED)
    
def get_all_data(request):
    data_queryset = Stock.objects.all().order_by('code')
    # Convert QuerySet to a list of dictionaries
    data_list = list(data_queryset.values())
    # Return the data as JSON response
    return JsonResponse(data_list, safe=False)

def get_stock_data(request, code):
    try:
        stock = Stock.objects.get(code=code.upper())
        data = {
            'code': stock.code,
            'name': stock.name,
            'sector': stock.sector,
            # Add other fields here
        }
        return JsonResponse(data)
    except Stock.DoesNotExist:
        return JsonResponse({'error': 'Saham tidak ditemukan'}, status=404)

def scrape_stock_data(stock_symbol):
    msg = ''

    try:
        # Retrieve the Stock instance based on the stock symbol
        stock_data = Stock.objects.get(code=stock_symbol)
        
        # Get the last recorded date for the specific stock
        last_price = Price.objects.filter(stock=stock_data).latest('date')
        stop_date = last_price.date.strftime('%b %d, %Y')
        
        # Define the URL and set up the webdriver
        url = f'https://finance.yahoo.com/quote/{stock_symbol}.JK/history?p={stock_symbol}.JK'
        path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Use headless browser
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Scrape data
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.BdT'))
        )
        
        for element in elements:
            row = element.find_elements(By.TAG_NAME, 'td')
            if last_price.date.strftime('%b %d, %Y') == row[0].text:
                msg = 'Data sudah paling baru'
                break

            if len(row) >= 5:
                date = row[0].text
                open_price = float(row[1].text.replace(',', ''))
                high_price = float(row[2].text.replace(',', ''))
                low_price = float(row[3].text.replace(',', ''))
                close_price = float(row[4].text.replace(',', ''))
                volume = int(row[6].text.replace(',', ''))

                # Create the Price instance and save it to the database within a transaction
                with transaction.atomic():
                    price_instance = Price(
                        stock=stock_data,
                        date=datetime.strptime(date, '%b %d, %Y'),
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume
                    )
                    price_instance.save()
                logging.info(f"Saved data for date: {date}")

                if date == stop_date:
                    msg = "Reached stop date. Exiting the loop"
                    break
            else:
                logging.warning("Row < 5")
    except Stock.DoesNotExist:
        msg = f"Stock with code '{stock_symbol}' not found."
        logging.error(msg)
    except Exception as e:
        msg = f"An error occurred: {str(e)}"
        logging.error(msg)
    finally:
        driver.quit()  # Close the browser session

    return msg

def scraping(request):
    stock_codes_query = Stock.objects.values_list('code', flat=True)
    stock_codes_list = ['BBCA']

    messages = []  # Store messages for each stock code
    for stock_code in stock_codes_list:
        msg = scrape_stock_data(stock_code)
        messages.append({'stock_code': stock_code, 'msg': msg})

    return JsonResponse({'messages': messages})

def api_view(request):
  # Load data from a CSV file
    param = request.GET.get('kode')
    if param is not None:
        stock_instance = get_object_or_404(Stock, code=param.upper())
        data_queryset = Price.objects.filter(stock=stock_instance).order_by('date')
        if len(data_queryset) == 0:
            return JsonResponse('Tidak ada data saham ini', safe=False)
            # Convert QuerySet to a list of dictionaries
        data_list = list(data_queryset.values())
        column_mapping = {
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'adj': 'Adj Close',
            'volume': 'Volume',
        }
        df = pd.DataFrame(data_list).rename(columns=column_mapping)
        
        # Determine local price extrema using rolling windows
        df['RollingMin'] = df['Close'].rolling(window=20).min()
        df['RollingMax'] = df['Close'].rolling(window=20).max()

        # Identify support levels
        df['SupportArea'] = ((abs(df['Close'] - df['RollingMin']) / df['RollingMin']) * 100) <= 3
        # Print the support and resistance levels

        # df['BodyLength'] = abs(df['Open'] - df['Close'])
        # df['UpperShadow'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        # df['LowerShadow'] = df[['Open', 'Close']].min(axis=1) - df['Low']

        # # Determine if a bullish hammer pattern is present
        # df['BullishHammer'] = (df['Close'] > df['Open']) & (df['BodyLength'] < df['LowerShadow']) & (df['LowerShadow'] > df['UpperShadow'] * 2)

        # Calculate RSI 
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean().abs()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Calculate the MACD line (12-day EMA minus 26-day EMA)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        # Calculate the signal line (9-day EMA of the MACD line)
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        df['MACD_Crossover'] = (macd_line > signal_line) & (macd_line.shift(1) < signal_line.shift(1))

        # df['Above_EMA_200'] = df['Close'] > df['Close'].rolling(window=200).mean()

        df['Engulfing'] = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
                                (df['High'] > df['High'].shift(1)) & (df['Low'] < df['Low'].shift(1))

        # # Add a column for the downtrend or consolidation condition
        # df['Downtrend_Consolidation'] = (df['Close'] < df['Close'].rolling(window=50).mean())

        # # Filter the DataFrame to get only the bullish engulfing patterns
        # bullish_engulfing_patterns = df[df['Engulfing'] & df['Downtrend_Consolidation']]

        # Define the input variables
        engulfing = ctrl.Antecedent(np.arange(0, 2, 1), 'engulfing')
        macd_crossover = ctrl.Antecedent(np.arange(0, 2, 1), 'macd_crossover')
        rsi = ctrl.Antecedent(np.arange(0, 101, 1), 'rsi')
        support_area = ctrl.Antecedent(np.arange(0, 2, 1), 'support_area')

        # above_ema_200 = ctrl.Antecedent(np.arange(0, 2, 1), 'above_ema_200')

        # Define the output variable
        entry_position = ctrl.Consequent(np.arange(0, 101, 1), 'entry_position')

        # membership function
        engulfing['no'] = fuzz.trimf(engulfing.universe, [0, 0, 0])
        engulfing['yes'] = fuzz.trimf(engulfing.universe, [1, 1, 1])

        macd_crossover['no'] = fuzz.trimf(macd_crossover.universe, [0, 0, 0])
        macd_crossover['yes'] = fuzz.trimf(macd_crossover.universe, [1, 1, 1])

        rsi['oversold'] = fuzz.trimf(rsi.universe, [0, 20, 45])
        rsi['neutral'] = fuzz.trimf(rsi.universe, [30, 50, 70])
        rsi['overbought'] = fuzz.trimf(rsi.universe, [60, 80, 100])

        support_area['no'] = fuzz.trimf(support_area.universe, [0,0,0])
        support_area['yes'] = fuzz.trimf(support_area.universe, [1,1,1])

        # above_ema_200['no'] = fuzz.trimf(above_ema_200.universe, [0, 0, 0])
        # above_ema_200['yes'] = fuzz.trimf(above_ema_200.universe, [1, 1, 1])


        # Define the membership functions for the entry position output variable
        entry_position['low'] = fuzz.trimf(entry_position.universe, [0, 0, 50])
        entry_position['high'] = fuzz.trimf(entry_position.universe, [50, 100, 100])

        # Define the rules for the fuzzy system
        rule1 = ctrl.Rule(rsi['oversold'] & macd_crossover['yes'], entry_position['high'])
        rule2 = ctrl.Rule(rsi['oversold'] & macd_crossover['no'], entry_position['high'])
        rule3 = ctrl.Rule(rsi['neutral'] & macd_crossover['yes'], entry_position['high'])
        rule4 = ctrl.Rule(rsi['neutral'] & macd_crossover['no'], entry_position['low'])
        # rule5 = ctrl.Rule(rsi['overbought'] & macd_crossover['yes'], entry_position['low'])
        rule6 = ctrl.Rule(rsi['overbought'] & macd_crossover['no'] , entry_position['low'])
        rule7 = ctrl.Rule(support_area['yes'], entry_position['high'])
        rule8 = ctrl.Rule(support_area['no'], entry_position['low'])
        rule9 = ctrl.Rule(support_area['yes'] & engulfing['yes'], entry_position['high'])
        rule10 = ctrl.Rule(support_area['no'] & engulfing['no'], entry_position['low'])

        # Create the control system and simulate it for each row of the data
        entry_position_ctrl = ctrl.ControlSystem(
            [
            rule1, 
            rule2, 
            rule3, 
            rule4, 
            #  rule5, 
            rule6,
            rule7,
            rule8,
            rule9,
            rule10,
            #  rule11,
            # #  rule12,
            #  rule13,
            ]
            )
        entry_position_simulation = ctrl.ControlSystemSimulation(entry_position_ctrl)

        # Loop through the data and predict the entry position for each row
        for i in range(len(df)):
            # Set the input values for the current row
            entry_position_simulation.input['rsi'] = df.loc[i, 'RSI']
            entry_position_simulation.input['macd_crossover'] = df.loc[i, 'MACD_Crossover']
            entry_position_simulation.input['support_area'] = df.loc[i, 'SupportArea']
            entry_position_simulation.input['engulfing'] = df.loc[i, 'Engulfing']
            # entry_position_simulation.input['engulfing'] = df.loc[i, 'Engulfing']
            # entry_position_simulation.input['above_ema_200'] = df.loc[i, 'Above_EMA_200']
            
            # Compute the output value
            entry_position_simulation.compute()
            
            # Save the predicted entry position for the current row
            df.loc[i, 'Entry_Position'] = entry_position_simulation.output['entry_position']
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        df['Date'] = df['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))

        data_json = df.to_json(orient='records')

        # Return the JSON response
        return JsonResponse(json.loads(data_json), safe=False)
    else:
        return JsonResponse('Tolong input kode saham !', safe=False)