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
            'sell': data_entry['Low'],
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
        data = Price.objects.filter(stock=stock).order_by('date')
        return JsonResponse(list(data.values()), safe=False)
    except Stock.DoesNotExist:
        return JsonResponse({'error': 'Saham tidak ditemukan'}, status=404, safe=False)

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
        # path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
        options = webdriver.EdgeOptions()
        # options.headless = True
        options.add_argument('headless')  # Use headless browser
        driver = webdriver.Edge(options=options)
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
    stock_codes_list = list(stock_codes_query)

    messages = []  # Store messages for each stock code
    for stock_code in stock_codes_list:
        msg = scrape_stock_data(stock_code)
        messages.append({'stock_code': stock_code, 'msg': msg})

    return JsonResponse({'messages': messages})

def scraping_single_stock(request, code):
    msg = ''
    try:
        msg = scrape_stock_data(code.upper())
    except Exception as e:
        msg = str(e)
        logging.error(msg)

    return JsonResponse({'messages': msg})

def clear_duplicate_data(code):
    try:
        msg = ''
        stock = Stock.objects.get(code=code.upper())
        prices = Price.objects.filter(stock=stock).order_by('date')
        stock_data = list(prices)

        previous_entry = None

        for current_entry in stock_data:
            if previous_entry and current_entry.date == previous_entry.date:
                Price.objects.filter(id=current_entry.id).delete()

            previous_entry = current_entry
        
        msg = 'Berhasil menghapus duplikasi data' + code.upper()

    except Exception as e:
        msg = str(e)
        logging.error(msg)

    return msg

def clear_data(request):
    stock_codes_query = Stock.objects.values_list('code', flat=True)
    stock_codes_list = list(stock_codes_query)

    messages = []  # Store messages for each stock code
    for stock_code in stock_codes_list:
        msg = clear_duplicate_data(stock_code)
        messages.append(msg)

    return JsonResponse({'messages': messages})


def api_view(request):

    param = request.GET.get('kode')
    if param is not None:
        stock_instance = get_object_or_404(Stock, code=param.upper())
        data_queryset = Price.objects.filter(stock=stock_instance).order_by('date')
        if len(data_queryset) == 0:
            return JsonResponse('Tidak ada data saham ini', safe=False)
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
        
        #BullishHammer Pattern
        df['BodyLength'] = abs(df['Open'] - df['Close'])
        upperShadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        lowerShadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['BullishHammer'] = (df['Close'] > df['Open']) & (df['BodyLength'] < lowerShadow) & (lowerShadow > upperShadow * 2)

        # Doji Pattern
        df['HighLowRange'] = df['High'] - df['Low']
        df['Doji'] = df['BodyLength'] <= (0.02 * df['HighLowRange'])

        # Stochastic
        df['Lowest Low'] = df['Close'].rolling(window=14).min()
        df['Highest High'] = df['Close'].rolling(window=14).max()
        df['%K'] = ((df['Close'] - df['Lowest Low']) / (df['Highest High'] - df['Lowest Low'])) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()

        # RSI 
        df['delta'] = df['Close'].diff()
        df['gain'] = df['delta'].where(df['delta'] > 0, 0)
        df['loss'] = -df['delta'].where(df['delta'] < 0, 0)
        df['avg_gain'] = df['gain'].rolling(window=14).mean()
        df['avg_loss'] = df['loss'].rolling(window=14).mean().abs()
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['RSI'] = 100 - (100 / (1 + df['rs']))

        # MACD
        df['ema_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = df['ema_12'] - df['ema_26']
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['MACD_GoldenCross'] = (df['macd_line'] > df['signal_line']) & (df['macd_line'].shift(1) < df['signal_line'].shift(1))
        df['MACD_DeathCross'] = (df['macd_line'] < df['signal_line']) & (df['macd_line'].shift(1) > df['signal_line'].shift(1))

        df['Engulfing'] = (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1)) & \
                                (df['High'] > df['High'].shift(1)) & (df['Low'] < df['Low'].shift(1))


        engulfing = ctrl.Antecedent(np.arange(0, 2, 1), 'engulfing')
        bullish_hammer = ctrl.Antecedent(np.arange(0, 2, 1), 'bullish_hammer')
        doji = ctrl.Antecedent(np.arange(0, 2, 1), 'doji')
        macd_goldencross = ctrl.Antecedent(np.arange(0, 2, 1), 'macd_goldencross')
        macd_deathcross = ctrl.Antecedent(np.arange(0, 2, 1), 'macd_deathcross')
        rsi = ctrl.Antecedent(np.arange(0, 101, 1), 'rsi')
        stochastic = ctrl.Antecedent(np.arange(0, 101, 1), 'stochastic')

        exit_position = ctrl.Consequent(np.arange(0, 101, 1), 'exit_position')
        entry_position = ctrl.Consequent(np.arange(0, 101, 1), 'entry_position')

        # membership function
        engulfing['no'] = fuzz.trimf(engulfing.universe, [0, 0, 0])
        engulfing['yes'] = fuzz.trimf(engulfing.universe, [1, 1, 1])

        bullish_hammer['no'] = fuzz.trimf(bullish_hammer.universe, [0, 0, 0])
        bullish_hammer['yes'] = fuzz.trimf(bullish_hammer.universe, [1, 1, 1])

        doji['no'] = fuzz.trimf(doji.universe, [0, 0, 0])
        doji['yes'] = fuzz.trimf(doji.universe, [1, 1, 1])

        macd_goldencross['no'] = fuzz.trimf(macd_goldencross.universe, [0, 0, 0])
        macd_goldencross['yes'] = fuzz.trimf(macd_goldencross.universe, [1, 1, 1])

        macd_deathcross['no'] = fuzz.trimf(macd_deathcross.universe, [0, 0, 0])
        macd_deathcross['yes'] = fuzz.trimf(macd_deathcross.universe, [1, 1, 1])

        rsi['oversold'] = fuzz.trimf(rsi.universe, [0, 15, 30])
        rsi['neutral'] = fuzz.trimf(rsi.universe, [30, 50, 70])
        rsi['overbought'] = fuzz.trimf(rsi.universe, [70, 85, 100])

        stochastic['oversold'] = fuzz.trimf(stochastic.universe, [0, 15, 30])
        stochastic['neutral'] = fuzz.trimf(stochastic.universe, [30, 50, 70])
        stochastic['overbought'] = fuzz.trimf(stochastic.universe, [70, 85, 100])

        exit_position['low'] = fuzz.trimf(exit_position.universe, [0, 25, 50])
        exit_position['high'] = fuzz.trimf(exit_position.universe, [50, 75, 100])

        entry_position['low'] = fuzz.trimf(entry_position.universe, [0, 25, 50])
        entry_position['high'] = fuzz.trimf(entry_position.universe, [50, 75, 100])
        
        # Define the rules for the fuzzy system
        entry_rule1 = ctrl.Rule(rsi['oversold'], entry_position['high'])
        entry_rule3 = ctrl.Rule(rsi['neutral'], entry_position['low'])
        entry_rule5 = ctrl.Rule(rsi['overbought'], entry_position['low'])
        entry_rule9 = ctrl.Rule(rsi['oversold'] & engulfing['yes'], entry_position['high'])
        entry_rule10 = ctrl.Rule(rsi['overbought'] & engulfing['no'], entry_position['low'])
        entry_rule11 = ctrl.Rule(rsi['oversold'] & bullish_hammer['yes'], entry_position['high'])
        entry_rule12 = ctrl.Rule(rsi['overbought'] & bullish_hammer['no'], entry_position['low'])
        entry_rule13 = ctrl.Rule(macd_goldencross['yes'], entry_position['high'])
        entry_rule14 = ctrl.Rule(macd_goldencross['no'], entry_position['low'])
        entry_rule15 = ctrl.Rule(doji['yes'] & rsi['oversold'], entry_position['high'])
        entry_rule16 = ctrl.Rule(doji['no'] & rsi['overbought'], entry_position['low'])
        entry_rule19 = ctrl.Rule(stochastic['oversold'], entry_position['high'])
        entry_rule20 = ctrl.Rule(stochastic['neutral'], entry_position['low'])
        entry_rule21 = ctrl.Rule(stochastic['overbought'], entry_position['low'])

        exit_rule1 = ctrl.Rule(rsi['overbought'], exit_position['high'])
        exit_rule4 = ctrl.Rule(rsi['neutral'], exit_position['low'])
        exit_rule6 = ctrl.Rule(rsi['oversold'], exit_position['low'])
        exit_rule9 = ctrl.Rule(macd_deathcross['yes'], exit_position['high'])
        exit_rule10 = ctrl.Rule(macd_deathcross['no'], exit_position['low'])
        exit_rule11 = ctrl.Rule(doji['yes'] & rsi['overbought'], exit_position['high'])
        exit_rule12 = ctrl.Rule(doji['no'] & rsi['oversold'], exit_position['low'])
        exit_rule13 = ctrl.Rule(stochastic['oversold'], exit_position['low'])
        exit_rule14 = ctrl.Rule(stochastic['neutral'], exit_position['low'])
        exit_rule15 = ctrl.Rule(stochastic['overbought'], exit_position['high'])

        entry_position_ctrl = ctrl.ControlSystem(
            [
            entry_rule1, 
            entry_rule3, 
            entry_rule5, 
            entry_rule9,
            entry_rule10,
            entry_rule11,
            entry_rule12,
            entry_rule13,
            entry_rule14,
            entry_rule15,
            entry_rule16,
            entry_rule19,
            entry_rule20,
            entry_rule21,
            ]
            )
        entry_position_simulation = ctrl.ControlSystemSimulation(entry_position_ctrl)

        exit_position_ctrl = ctrl.ControlSystem(
            [
            exit_rule1, 
            exit_rule4, 
            exit_rule6, 
            exit_rule9,
            exit_rule10,
            exit_rule11,
            exit_rule12,
            exit_rule13,
            exit_rule14,
            exit_rule15,
            ]
            )
        exit_position_simulation = ctrl.ControlSystemSimulation(exit_position_ctrl)

        # Loop through the data and predict the entry entry_position for each row
        for i in range(len(df)):
            # Set the input values for the current row
            entry_position_simulation.input['rsi'] = df.loc[i, 'RSI']
            entry_position_simulation.input['stochastic'] = df.loc[i, '%D']
            entry_position_simulation.input['macd_goldencross'] = df.loc[i, 'MACD_GoldenCross']
            entry_position_simulation.input['engulfing'] = df.loc[i, 'Engulfing']
            entry_position_simulation.input['bullish_hammer'] = df.loc[i, 'BullishHammer']
            entry_position_simulation.input['doji'] = df.loc[i, 'Doji']
            
            entry_position_simulation.compute()

            exit_position_simulation.input['rsi'] = df.loc[i, 'RSI']
            exit_position_simulation.input['stochastic'] = df.loc[i, '%D']
            exit_position_simulation.input['macd_deathcross'] = df.loc[i, 'MACD_DeathCross']
            exit_position_simulation.input['doji'] = df.loc[i, 'Doji']

            exit_position_simulation.compute()
            
            df.loc[i, 'Entry_Position'] = entry_position_simulation.output['entry_position']
            df.loc[i, 'Exit_Position'] = exit_position_simulation.output['exit_position']
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        df['Date'] = df['Date'].apply(lambda x: x.strftime('%Y-%m-%d'))

        data_json = df.to_json(orient='records')

        # Return the JSON response
        return JsonResponse(json.loads(data_json), safe=False)
    else:
        return JsonResponse('Tolong input kode saham !', safe=False)